"""Who may use the hosted app (Phase 4): the owner grants access per person, by email."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "app"))
from access import PRINCIPAL_HEADER, access, page_specs  # noqa: E402


def test_local_use_needs_no_sign_in() -> None:
    assert access({}, hosted=False, allowed="")[0]


def test_hosted_use_needs_a_signed_in_allowed_email() -> None:
    assert access({}, hosted=True, allowed="a@x.org") == (False, "Sign in is required. Open the app's address again "
                                                                  "to sign in.")
    ok, message = access({PRINCIPAL_HEADER: "eve@x.org"}, hosted=True, allowed="a@x.org")
    assert not ok and "eve@x.org" in message and "Ask the owner for access" in message
    assert access({PRINCIPAL_HEADER.lower(): " A@X.org "}, hosted=True, allowed="b@x.org; a@x.org") == (True, "a@x.org")


def test_hosted_pages_leave_out_the_local_labeling_helper() -> None:
    local, hosted = page_specs(hosted=False), page_specs(hosted=True)
    assert "views/labeling.py" in [p.path for p in local] and "views/labeling.py" not in [p.path for p in hosted]
    assert [p.path for p in hosted] == [p.path for p in local if p.path != "views/labeling.py"]


def test_hosted_app_without_sign_in_shows_only_the_sign_in_notice(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOSTED", "1")
    monkeypatch.setenv("ALLOWED_USERS", "owner@x.org")
    at = AppTest.from_file(str(ROOT / "app/streamlit_app.py"), default_timeout=60).run()
    assert not at.exception and any("Sign in is required" in w.value for w in at.warning)
    assert not at.text_input  # no API box, no Reviewer box: nothing past the gate


FAKE_AZ = """#!/usr/bin/env bash
if [ "$1 $2" = "containerapp show" ]; then cat "$AZ_STATE"; exit 0; fi
if [ "$1 $2" = "containerapp update" ]; then
  for a in "$@"; do case "$a" in ALLOWED_USERS=*) printf '%s' "${a#ALLOWED_USERS=}" > "$AZ_STATE";; esac; done; exit 0
fi
exit 1
"""


def grant(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    (bin_dir / "az").write_text(FAKE_AZ)
    (bin_dir / "az").chmod(0o755)
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "AZ_STATE": str(tmp_path / "state"),
           "AZURE_SUBSCRIPTION_ID": "sub", "RESOURCE_GROUP": "rg", "APP_NAME": "app"}
    return subprocess.run(["bash", str(ROOT / "scripts/grant_access.sh"), *args], env=env, capture_output=True,
                          text=True)


def test_grant_access_adds_and_removes_one_email(tmp_path: Path) -> None:
    (tmp_path / "state").write_text("owner@x.org")
    assert grant(tmp_path, "add", "Guest@X.org").returncode == 0
    assert (tmp_path / "state").read_text() == "guest@x.org,owner@x.org"
    assert grant(tmp_path, "add", "guest@x.org").returncode == 0  # adding twice keeps one
    assert (tmp_path / "state").read_text() == "guest@x.org,owner@x.org"
    assert grant(tmp_path, "remove", "owner@x.org").returncode == 0
    assert (tmp_path / "state").read_text() == "guest@x.org"
    listed = grant(tmp_path, "list")
    assert listed.returncode == 0 and listed.stdout.strip() == "guest@x.org"
    assert grant(tmp_path, "add").returncode != 0  # an email is required


def test_grant_access_starts_from_nobody_when_the_setting_is_unset(tmp_path: Path) -> None:
    (tmp_path / "state").write_text("None")  # what az prints for a missing setting
    assert grant(tmp_path, "list").stdout.strip() == ""
    assert grant(tmp_path, "add", "owner@x.org").returncode == 0 and (tmp_path / "state").read_text() == "owner@x.org"
