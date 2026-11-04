"""Spec Review Copilot: the engineer review app (spec 8.15). Run with `uv run streamlit run app/streamlit_app.py`.

The API must be running too: `uv run specreview serve`. Hosted (HOSTED=1), only allowed emails get in.
"""

import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from access import access, page_specs  # noqa: E402
from api_client import ApiClient, ApiError  # noqa: E402
from views.common import md  # noqa: E402

st.set_page_config(page_title="Spec Review Copilot", layout="wide")
hosted = os.environ.get("HOSTED", "").strip().lower() in ("1", "true", "yes")
allowed, who = access(st.context.headers, hosted, os.environ.get("ALLOWED_USERS", ""))
if not allowed:
    st.title("Spec Review Copilot")
    st.warning(who)
    st.stop()


@st.fragment(run_every="10s")
def watch_job() -> None:
    """While a job runs, check it from every page. Hosted, the API scales to zero after minutes without
    requests, which would end the job; a finished job redraws the app once so the run picker lists it."""
    job_id = st.session_state.get("job_id")
    if not job_id or st.session_state.get("job_listed") == job_id:
        return
    try:
        job = api.job(job_id)
    except ApiError:
        return
    if job["status"] in ("queued", "running"):
        st.caption(f"Running {job['package_id']}: stage {job['stages_done']} of {job['stages_total']}")
    elif job["status"] == "done":
        st.session_state["run_id"] = job["run_id"]
        st.session_state["job_listed"] = job_id
        st.rerun()


with st.sidebar:
    st.title("Spec Review Copilot")
    default_url = os.environ.get("API_URL", "http://127.0.0.1:8000")
    url = default_url if hosted else st.text_input("API", default_url, key="api_url")  # hosted: fixed, internal
    if "api" not in st.session_state or getattr(st.session_state["api"], "base_url", url) != url:
        st.session_state["api"] = ApiClient(url)
    api: ApiClient = st.session_state["api"]
    try:
        runs = api.runs()
    except ApiError as exc:
        st.error(exc.detail)
        runs = []
    labels = {r["run_id"]: f"{r['package_id']} · {r['run_id']} · {r['requirements']} items, "
                           f"{r['unreviewed']} to review" + ("" if r.get("status", "done") == "done" else
                                                              f" · {r['status']}") for r in runs}
    ids = list(labels)
    current = st.session_state.get("run_id")
    wanted = st.query_params.get("run")  # a citation link opens its run; the address then follows the picker
    if wanted in ids and st.session_state.get("url_run") != wanted:
        current = wanted
    if ids:
        st.session_state["run_id"] = st.selectbox("Run", ids, index=ids.index(current) if current in ids else 0,
                                                  format_func=labels.__getitem__)
        st.query_params["run"] = st.session_state["url_run"] = st.session_state["run_id"]
        picked = next(r for r in runs if r["run_id"] == st.session_state["run_id"])
        if (status := picked.get("status", "done")) == "running":
            st.info("This run is still running; its items fill in as it goes.")
        elif status != "done":
            why = {"failed": f"it failed ({md(picked.get('error') or 'no reason recorded')})",
                   "interrupted": "the API stopped while it ran",
                   "incomplete": "its last file, requirements.xlsx, is missing"}.get(status, status)
            st.warning(f"This run did not finish: {why}. Its items may be incomplete.")
    if hosted:  # every decision is recorded under the signed-in account
        st.session_state["reviewer"] = who
        st.caption(f"Signed in as {who}")
    else:
        name = st.text_input("Reviewer", st.session_state.get("reviewer") or st.query_params.get("reviewer", ""),
                             key="reviewer_name").strip()
        st.session_state["reviewer"] = name
        if name:  # a reload starts a new session, so the address keeps the name
            st.query_params["reviewer"] = name
        else:
            st.query_params.pop("reviewer", None)
    st.caption("The tool drafts; the engineer decides. Nothing is final until reviewed.")
    watch_job()  # inside the sidebar: a fragment's own reruns may write only where it was called


st.navigation([st.Page(p.path, title=p.title, icon=p.icon, default=p.default) for p in page_specs(hosted)]).run()
