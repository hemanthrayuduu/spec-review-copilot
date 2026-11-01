"""Outputs: generate the five drafts and download each one (spec 8.16)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # app/ on the path, whether run alone or by the shell

import streamlit as st  # noqa: E402

from api_client import ApiError  # noqa: E402
from views.common import context, show_error  # noqa: E402

api, run_id, _ = context()
st.header("Outputs")
st.write("The compliance matrix, a marked-up PDF per document, the exceptions and clarifications letter, the "
         "clarification questions, and the addendum diff. They use the latest review decisions.")
if st.button("Generate outputs", key="out_generate", type="primary"):
    try:
        st.session_state[f"outputs_{run_id}"] = api.outputs(run_id)
    except ApiError as exc:
        show_error(exc)
result = st.session_state.get(f"outputs_{run_id}")
if result:
    if result["draft_banner"]:
        st.warning(result["draft_banner"])
    for name in result["files"]:
        try:
            st.download_button(f"Download {name}", api.download(run_id, name), file_name=name, key=f"dl_{name}")
        except ApiError as exc:
            show_error(exc)
    for note in result["skipped"]:
        st.caption(f"Skipped: {note}")
