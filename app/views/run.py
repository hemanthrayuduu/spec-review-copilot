"""Run a package: upload PDFs or run the Lakeview sample, then watch the job stage by stage."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # app/ on the path, whether run alone or by the shell

import streamlit as st  # noqa: E402

from api_client import ApiError  # noqa: E402
from views.common import STATUSES, context, show_error  # noqa: E402,F401

api, _, _ = context(need_run=False)
st.header("Run a package")
left, right = st.columns(2)
with left:
    files = st.file_uploader("Bid package PDFs", type=["pdf"], accept_multiple_files=True, key="run_files")
    name = st.text_input("Package name", key="run_name")
    if st.button("Start", key="run_start", disabled=not files or not name):
        try:
            st.session_state["job_id"] = api.upload(name, [(f.name, f.getvalue()) for f in files or []])["job_id"]
        except ApiError as exc:
            show_error(exc)
with right:
    st.write("Or run the synthetic Lakeview package, which has an addendum and planted traps.")
    if st.button("Run the Lakeview sample", key="run_sample"):
        try:
            st.session_state["job_id"] = api.sample("lakeview")["job_id"]
        except ApiError as exc:
            show_error(exc)


@st.fragment(run_every="2s")
def progress() -> None:
    job_id = st.session_state.get("job_id")
    if not job_id:
        return
    try:
        job = api.job(job_id)
    except ApiError as exc:
        show_error(exc)
        return
    st.progress(job["stages_done"] / job["stages_total"],
                text=f"{job['package_id']}: {job['status']}, stage {job['stage'] or '-'} "
                     f"({job['stages_done']} of {job['stages_total']})")
    if job["status"] == "done":
        st.session_state["run_id"] = job["run_id"]
        st.success(f"Run {job['run_id']} is ready. Open the Brief or the Checklist.")
    elif job["status"] == "failed":
        st.error(f"The run failed: {job['error']}")


progress()
