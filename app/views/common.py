"""What every review page needs: the API client, the open run, and the reviewer, from the session."""

import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import quote, urlencode

import streamlit as st

from api_client import ApiClient, ApiError

STATUSES = ("comply", "comply_with_clarification", "deviation", "needs_engineer", "not_applicable")
_MARKDOWN = re.compile(r"([\\`*_{}\[\]()#+\-.!|~<>$:&])")


def md(text: object) -> str:
    """Untrusted text (PDF lines, AI reasons, notes, file names) shown literally inside Markdown.

    Every Markdown character is escaped, so "$500 ... $1,500" is not math and [x](url) is not a link or an image.
    """
    return _MARKDOWN.sub(r"\\\1", str(text))


def context(need_run: bool = True) -> tuple[ApiClient, str, str]:
    api = st.session_state.get("api")
    if api is None:
        st.info("Open the app with `uv run streamlit run app/streamlit_app.py` so it can reach the API.")
        st.stop()
    run_id = st.session_state.get("run_id") or ""
    if need_run and not run_id:
        st.info("Pick a run in the sidebar, or start one on the Run a package page.")
        st.stop()
    return api, run_id, st.session_state.get("reviewer") or ""


def show_error(exc: ApiError) -> None:
    st.error(exc.detail if exc.status == 0 else f"The API said: {md(exc)}")  # status 0 is our own message



def item_label(item: Mapping[str, Any]) -> str:
    """The checklist picker's line: where the item is, its parameter and value, then the sentence. Two values
    from one sentence, like a pump's flow and head, would otherwise look the same."""
    what = " ".join(str(x) for x in (item.get("parameter"), item.get("value"), item.get("unit")) if x)
    where = f"[{item['code'] or '-'}] {item['section_number'] or '-'} {item['paragraph_path']}: "
    return where + (f"{what} · " if what else "") + item["source_text"][:90]


def group_rows(items: list[dict[str, Any]], groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per review group, in review order, empty groups included, so the table keeps its shape."""
    rows = []
    for g in groups:
        mine = [i for i in items if i["group"] == g["group"]]
        reviewed = sum(i["reviewed"] for i in mine)
        rows.append({"Area": g["area"], "Group": g["group"], "Items": len(mine),
                     "Deviations": sum(i["final_status"] == "deviation" for i in mine),
                     "Need an engineer": sum(i["final_status"] == "needs_engineer" for i in mine),
                     "Not reviewed": len(mine) - reviewed,
                     "Reviewed": reviewed / len(mine) if mine else 0.0})
    return rows


def show_groups(items: list[dict[str, Any]], groups: list[dict[str, Any]]) -> None:
    st.dataframe(group_rows(items, groups), hide_index=True, use_container_width=True, column_config={
        "Reviewed": st.column_config.ProgressColumn("Reviewed", min_value=0.0, max_value=1.0, format="percent")})


def flag_text(item: Mapping[str, Any]) -> str:
    return ", ".join(f.replace("_", " ") for f in item["red_flags"])


def source_link(run_id: str, req_id: str, cite: str) -> str:
    """The Source viewer at this item, in a new tab: the run and the item travel in the address."""
    return "/source?" + urlencode({"run": run_id, "req": req_id, "cite": cite}, quote_via=quote)


def evidence_line(e: Mapping[str, Any]) -> str:
    """One evidence bullet. A public source links to its page; a fictional one says so and has no link."""
    where = md(f"{e['ref']} p.{e['page'] or '-'}")
    url = (e.get("url") or "").replace("(", "%28").replace(")", "%29").replace(" ", "%20")
    cite = f"[{where}]({url})" if url else where
    tag = "" if e["origin"] != "synthetic" else (
        " · **SYNTHETIC** (fictional data sheet)" if e.get("page_view") else " · **SYNTHETIC** (fictional, no source)")
    return f"- `{e['evidence_id']}` ({e['basis'] or '-'}, {cite}){tag}: {md(e['text'][:200])}"


EVIDENCE_FILTERS = ("All", "Real sources only", "Any real source", "Uses synthetic data")


def evidence_kind(item: Mapping[str, Any]) -> str:
    """What the AI's decision rests on: real (public sources only), real + synthetic, synthetic, or none cited."""
    public = any(e["origin"] == "public" for e in item["evidence"])
    synthetic = bool(item["uses_synthetic"]) or any(e["origin"] == "synthetic" for e in item["evidence"])
    if public:
        return "real + synthetic" if synthetic else "real"
    return "synthetic" if synthetic else "none"


def evidence_matches(item: Mapping[str, Any], choice: str) -> bool:
    kind = evidence_kind(item)
    return {"All": True, "Real sources only": kind == "real",
            "Any real source": kind in ("real", "real + synthetic"),
            "Uses synthetic data": kind in ("synthetic", "real + synthetic")}[choice]


def real_first(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Public sources before synthetic rows, each in the order the AI cited them."""
    return sorted(evidence, key=lambda e: e["origin"] != "public")


ANSWER_FILTERS = ("All", "AI agrees", "AI disagrees", "No label")


def answer_text(key: Mapping[str, Any], req_id: str) -> str:
    """The table cell: the labeled status with ✓ when the AI agrees, ✗ when not; "-" for an unlabeled item."""
    found = key["items"].get(req_id)
    return "-" if found is None else f"{found['expected']} {'✓' if found['agrees'] else '✗'}"


def answer_matches(key: Mapping[str, Any], req_id: str, choice: str) -> bool:
    found = key["items"].get(req_id)
    return {"All": True, "AI agrees": bool(found and found["agrees"]), "AI disagrees": bool(found and not found["agrees"]),
            "No label": found is None}[choice]


def answer_line(key: Mapping[str, Any], item: Mapping[str, Any]) -> str | None:
    """The detail line for one item, or None when the run has no answer key or the item no label."""
    found = key["items"].get(item["req_id"]) if key.get("available") else None
    if found is None:
        return None
    verdict = "the AI agrees ✓" if found["agrees"] else f"the AI disagrees ✗ (it said {md(item['ai_status'] or 'not matched')})"
    trap = f" · planted trap {found['trap']}" if found["trap"] else ""
    return f"**Right answer:** {md(found['expected'])} · {verdict}{trap}"


def show_answer_key(key: Mapping[str, Any]) -> None:
    st.subheader("Against the answer key")
    cols = st.columns(4)
    cols[0].metric("AI status agrees", f"{key['correct']} of {key['matched']}")
    cols[1].metric("Status accuracy", f"{key['accuracy_matched']:.3f}" if key["accuracy_matched"] is not None else "-")
    cols[2].metric("Requirement recall", f"{key['recall']:.3f}")
    cols[3].metric("Precision", f"{key['precision']:.3f}")
    st.caption(f"Scored like `specreview eval dev`: each extracted requirement is paired with its labeled one. "
               f"{key['labeled']} labeled requirements; {key['missing']} were not extracted.")


def cited_page_pick(item: Mapping[str, Any], key: str) -> dict[str, Any] | None:
    """A picker over the evidence whose cited page we hold; it sits next to the evidence list."""
    held = [e for e in real_first(item["evidence"]) if e.get("page_view")]
    if not held:
        return None
    names = {e["evidence_id"]: f"{e['evidence_id']} · {e['ref']} p.{e['page']}"
                               + (" (fictional data sheet)" if e["origin"] == "synthetic" else "") for e in held}
    pick = st.selectbox("View a cited page", [None, *names], format_func=lambda x: "Choose evidence" if x is None
                        else names[x], key=key)
    return next((e for e in held if e["evidence_id"] == pick), None)


def show_cited_page(api: Any, run_id: str, chosen: Mapping[str, Any] | None, key: str) -> None:
    """The chosen cited page at full width: the cited line enlarged, and the whole page on request."""
    if chosen is None:
        return
    where = f"{chosen['ref']} page {chosen['page']}"
    note = " · FICTIONAL demo data, not from any manufacturer" if chosen["origin"] == "synthetic" else ""
    st.subheader(f"Cited page: {where}")
    try:
        st.image(api.evidence_png(run_id, chosen["evidence_id"], zoom=True), use_container_width=True,
                 caption=f"Enlarged: the cited line on {where}{note}")
        if st.checkbox("Show the whole page", key=f"{key}_whole"):
            st.image(api.evidence_png(run_id, chosen["evidence_id"]), caption=f"{where}{note}",
                     use_container_width=True)
    except ApiError as exc:
        show_error(exc)
