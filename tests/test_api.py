"""The API service: jobs, runs, items, decisions, page images, and outputs (Phase 3, spec 5 layer 2)."""

import json
import time
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from api_fixtures import api_settings, client_with_run, failing_runner, fake_runner
from run_fixtures import R_COMPLY, R_DEVIATION, make_package, make_run
from spec_review.api.main import create_app, safe_name

def _pdf_bytes(tmp_path: Path) -> bytes:
    from pdf_fixtures import make_pdf
    return make_pdf(tmp_path / "up.pdf", ["<p>Screens shall be stainless.</p>"]).read_bytes()


def _wait(client, job_id: str) -> dict:  # type: ignore[no-untyped-def]
    for _ in range(200):
        job = client.get(f"/jobs/{job_id}").json()
        if job["status"] in ("done", "failed"):
            return job
        time.sleep(0.02)
    raise AssertionError("job did not finish")


def test_upload_runs_a_job_and_reports_progress(tmp_path: Path) -> None:
    client, settings = client_with_run(tmp_path)
    r = client.post("/jobs/upload", data={"package_name": "My Package"},
                    files=[("files", ("specs.pdf", _pdf_bytes(tmp_path), "application/pdf"))])
    assert r.status_code == 200, r.text
    job = _wait(client, r.json()["job_id"])
    assert job["status"] == "done" and job["stages_done"] == 3 and job["run_id"]
    assert job["stages_total"] == 13 and job["stage"] == "addenda"
    assert any(p.name.startswith("my_package-") for p in settings.uploads_dir.iterdir())


def test_upload_names_are_made_safe_and_non_pdfs_refused(tmp_path: Path) -> None:  # Review Focus 1
    client, settings = client_with_run(tmp_path)
    r = client.post("/jobs/upload", data={"package_name": "x"},
                    files=[("files", ("../../etc/x.pdf", _pdf_bytes(tmp_path), "application/pdf"))])
    assert r.status_code == 200 and not (tmp_path / "etc").exists()
    saved = [p for p in settings.uploads_dir.rglob("*.pdf")]
    assert [p.name for p in saved] == ["x.pdf"] and all(settings.uploads_dir in p.parents for p in saved)
    bad = client.post("/jobs/upload", data={"package_name": "x"}, files=[("files", ("notes.txt", b"hi", "text/plain"))])
    assert bad.status_code == 400


def test_safe_name() -> None:
    assert safe_name("../../etc/My Spec (final).PDF") == "My_Spec__final_.pdf"
    assert safe_name("a/b\\c.pdf") == "c.pdf" and safe_name("..hidden.pdf") == "hidden.pdf"


def test_sample_refuses_paths_outside_dev(tmp_path: Path) -> None:
    client, settings = client_with_run(tmp_path)
    assert client.post("/jobs/sample", json={"package": "../../test/x"}).status_code == 400
    (settings.raw_dir / "dev" / "lakeview").mkdir(parents=True)
    r = client.post("/jobs/sample", json={"package": "lakeview"})
    assert r.status_code == 200 and _wait(client, r.json()["job_id"])["status"] == "done"


def test_a_failed_job_reports_its_error(tmp_path: Path) -> None:
    client, settings = client_with_run(tmp_path, runner=failing_runner)
    (settings.raw_dir / "dev" / "lakeview").mkdir(parents=True)
    job = _wait(client, client.post("/jobs/sample", json={"package": "lakeview"}).json()["job_id"])
    assert job["status"] == "failed" and job["error"] == "RuntimeError: extraction exploded"


def test_unknown_job_is_404(tmp_path: Path) -> None:
    client, _ = client_with_run(tmp_path)
    assert client.get("/jobs/nope").status_code == 404


def test_runs_list_the_finished_run(tmp_path: Path) -> None:
    client, _ = client_with_run(tmp_path)
    [run] = client.get("/runs").json()
    assert (run["run_id"], run["package_id"], run["requirements"], run["matched"], run["unreviewed"]) == \
        ("run1", "pkg", 3, True, 3)


def test_stage_files_are_served_by_name_only(tmp_path: Path) -> None:
    client, _ = client_with_run(tmp_path)
    assert client.get("/runs/run1/stage/match").json()["package_id"] == "pkg"
    assert client.get("/runs/run1/stage/secrets").status_code == 404
    assert client.get("/runs/..%2F..%2Fetc/stage/match").status_code == 404


def test_items_show_the_saved_decision(tmp_path: Path) -> None:
    client, _ = client_with_run(tmp_path)
    r = client.post("/runs/run1/decisions", json={"req_id": R_COMPLY, "final_status": "deviation", "reviewer": "hr",
                                                  "note": "panels are 304L"})
    assert r.status_code == 200
    item = next(i for i in client.get("/runs/run1/items").json() if i["req_id"] == R_COMPLY)
    assert (item["final_status"], item["reviewed"], item["code"], item["note"], item["ai_status"]) == \
        ("deviation", True, "D", "panels are 304L", "comply")
    assert [d["final_status"] for d in client.get(f"/runs/run1/decisions/{quote(R_COMPLY, safe='')}/history").json()] == ["deviation"]


def test_an_approved_deviation_lands_in_review_exceptions(tmp_path: Path) -> None:
    client, settings = client_with_run(tmp_path)
    client.post("/runs/run1/decisions", json={"req_id": R_DEVIATION, "final_status": "deviation", "reviewer": "hr"})
    assert R_DEVIATION in (settings.knowledge_dir / "review_exceptions.csv").read_text()


def test_decision_for_an_unknown_requirement_is_404_and_writes_nothing(tmp_path: Path) -> None:  # Review Focus 2
    client, _ = client_with_run(tmp_path)
    r = client.post("/runs/run1/decisions", json={"req_id": "nope", "final_status": "comply", "reviewer": "hr"})
    assert r.status_code == 404 and client.get("/runs/run1/decisions/nope/history").json() == []


def test_decision_with_a_bad_status_is_422(tmp_path: Path) -> None:
    client, _ = client_with_run(tmp_path)
    r = client.post("/runs/run1/decisions", json={"req_id": R_COMPLY, "final_status": "maybe", "reviewer": "hr"})
    assert r.status_code == 422


def test_page_png_renders_with_a_highlight(tmp_path: Path) -> None:
    client, _ = client_with_run(tmp_path)
    plain = client.get("/runs/run1/page/specs/1.png")
    r = client.get("/runs/run1/page/specs/1.png", params={"req_id": R_COMPLY})
    assert r.status_code == 200 and r.headers["content-type"] == "image/png" and r.content[:4] == b"\x89PNG"
    assert r.content != plain.content  # the highlight changed the image
    assert client.get("/runs/run1/page/specs/9.png").status_code == 404
    assert client.get("/runs/run1/page/..%2Fsecret/1.png").status_code == 404


def test_outputs_generate_and_download(tmp_path: Path) -> None:
    client, _ = client_with_run(tmp_path)
    res = client.post("/runs/run1/outputs").json()
    assert "compliance_matrix.xlsx" in res["files"] and "specs_marked.pdf" in res["files"]
    r = client.get("/runs/run1/outputs/addendum_diff.md")
    assert r.status_code == 200 and "7 years" in r.text
    assert client.get("/runs/run1/outputs/run.json").status_code == 404


def test_addenda_route_pairs_before_and_after(tmp_path: Path) -> None:
    client, _ = client_with_run(tmp_path)
    [replace, date] = client.get("/runs/run1/addenda").json()
    assert replace["target_paragraph"] == "2.01.B" and "5 years" in replace["before"][0]["text"]
    assert "7 years" in replace["after"][0]["text"] and replace["items"][0]["req_id"] == R_DEVIATION
    assert date["action"] == "revise_date" and date["new_text"] == "December 15, 2026."
    assert replace["after_placeholder"] == "(no new text found)"  # final review: "(deleted)" only for a deletion


def test_upload_keeps_two_files_whose_safe_names_collide(tmp_path: Path) -> None:
    """Final review: "Spec (1).pdf" and "Spec [1].pdf" both became Spec__1_.pdf, and one file was lost."""
    client, settings = client_with_run(tmp_path)
    pdf = _pdf_bytes(tmp_path)
    r = client.post("/jobs/upload", data={"package_name": "x"},
                    files=[("files", ("Spec (1).pdf", pdf, "application/pdf")),
                           ("files", ("Spec [1].pdf", pdf + b"\n", "application/pdf"))])
    assert r.status_code == 200, r.text
    assert sorted(p.name for p in settings.uploads_dir.rglob("*.pdf")) == ["Spec__1_.pdf", "Spec__1__2.pdf"]


def test_runs_skip_a_folder_with_an_unreadable_run_file(tmp_path: Path) -> None:
    """Final review: one broken run.json made GET /runs fail, which emptied the app's run picker."""
    client, settings = client_with_run(tmp_path)
    (settings.runs_dir / "broken").mkdir()
    (settings.runs_dir / "broken" / "run.json").write_text("{")
    r = client.get("/runs")
    assert r.status_code == 200 and [x["run_id"] for x in r.json()] == ["run1"]


def test_page_png_serves_a_document_in_a_subfolder(tmp_path: Path) -> None:
    """Final review: doc_id "sub/specs" (spec 7) could not reach the page route."""
    settings = api_settings(tmp_path)
    pkg = make_package(tmp_path)
    (pkg / "sub").mkdir()
    (pkg / "specs.pdf").rename(pkg / "sub" / "specs.pdf")
    run_dir = make_run(settings.runs_dir, pkg)
    extract = json.loads((run_dir / "extract.json").read_text())
    for req in extract["requirements"]:
        req["doc_id"] = "sub/specs"
    (run_dir / "extract.json").write_text(json.dumps(extract))
    client = TestClient(create_app(settings, runner=fake_runner))
    r = client.get("/runs/run1/page/sub%2Fspecs/1.png", params={"req_id": R_COMPLY})
    assert r.status_code == 200 and r.content[:4] == b"\x89PNG"


def test_page_png_serves_a_pdf_with_an_upper_case_suffix(tmp_path: Path, case_sensitive_disk: None) -> None:
    """Code review: the page route looked for specs.pdf, so Specs.PDF on a Linux disk gave 404."""
    settings = api_settings(tmp_path)
    pkg = make_package(tmp_path)
    (pkg / "specs.pdf").rename(pkg / "specs.PDF")
    make_run(settings.runs_dir, pkg)
    client = TestClient(create_app(settings, runner=fake_runner))
    assert client.get("/runs/run1/page/specs/1.png").status_code == 200


@pytest.mark.parametrize("run_id", ["%2e%2e", "%2e", ".hidden"])
def test_a_dot_name_is_never_a_run(tmp_path: Path, run_id: str) -> None:
    """Code review: run id ".." passed the check and pointed at the folder above runs/."""
    client, settings = client_with_run(tmp_path)
    (settings.runs_dir / ".hidden").mkdir()
    assert client.get(f"/runs/{run_id}/decisions/x/history").status_code == 404
