"""What every review page needs: the API client, the open run, and the reviewer, from the session."""

import streamlit as st

from api_client import ApiClient, ApiError

STATUSES = ("comply", "comply_with_clarification", "deviation", "needs_engineer", "not_applicable")


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
    st.error(exc.detail if exc.status == 0 else f"The API said: {exc}")
