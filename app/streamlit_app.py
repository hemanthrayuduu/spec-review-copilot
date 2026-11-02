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

st.set_page_config(page_title="Spec Review Copilot", layout="wide")
hosted = os.environ.get("HOSTED", "").strip().lower() in ("1", "true", "yes")
allowed, who = access(st.context.headers, hosted, os.environ.get("ALLOWED_USERS", ""))
if not allowed:
    st.title("Spec Review Copilot")
    st.warning(who)
    st.stop()

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
                           f"{r['unreviewed']} to review" for r in runs}
    ids = list(labels)
    current = st.session_state.get("run_id")
    if ids:
        st.session_state["run_id"] = st.selectbox("Run", ids, index=ids.index(current) if current in ids else 0,
                                                  format_func=labels.__getitem__)
    if hosted:  # every decision is recorded under the signed-in account
        st.session_state["reviewer"] = who
        st.caption(f"Signed in as {who}")
    else:
        st.session_state["reviewer"] = st.text_input("Reviewer", st.session_state.get("reviewer", ""))
    st.caption("The tool drafts; the engineer decides. Nothing is final until reviewed.")

st.navigation([st.Page(p.path, title=p.title, icon=p.icon, default=p.default) for p in page_specs(hosted)]).run()
