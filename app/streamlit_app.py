"""Spec Review Copilot: the engineer review app (spec 8.15). Run with `uv run streamlit run app/streamlit_app.py`.

The API must be running too: `uv run specreview serve`.
"""

import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from api_client import ApiClient, ApiError  # noqa: E402

st.set_page_config(page_title="Spec Review Copilot", layout="wide")

with st.sidebar:
    st.title("Spec Review Copilot")
    url = st.text_input("API", os.environ.get("API_URL", "http://127.0.0.1:8000"), key="api_url")
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
    st.session_state["reviewer"] = st.text_input("Reviewer", st.session_state.get("reviewer", ""))
    st.caption("The tool drafts; the engineer decides. Nothing is final until reviewed.")

pages = [st.Page("views/run.py", title="Run a package", icon="▶️"),
         st.Page("views/brief.py", title="Brief", icon="📋", default=True),
         st.Page("views/checklist.py", title="Checklist", icon="✅"),
         st.Page("views/source.py", title="Source viewer", icon="📄"),
         st.Page("views/addenda.py", title="Addenda changes", icon="📝"),
         st.Page("views/outputs.py", title="Outputs", icon="📦"),
         st.Page("views/labeling.py", title="Labeling helper (local)", icon="🏷️")]
st.navigation(pages).run()
