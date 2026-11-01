"""Addenda changes: each change with the text before and after, and the requirements it touched."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # app/ on the path, whether run alone or by the shell

import streamlit as st  # noqa: E402

from api_client import ApiError  # noqa: E402
from views.common import context, show_error  # noqa: E402

api, run_id, _ = context()
try:
    changes = api.addenda(run_id)
except ApiError as exc:
    show_error(exc)
    st.stop()
st.header("Addenda changes")
if not changes:
    st.info("This package has no addendum changes.")
for c in changes:
    target = f" {c['target_paragraph']} in Section {c['target_section']}" if c["target_paragraph"] else ""
    with st.container(border=True):
        st.markdown(f"**{c['change_id']}: {c['addendum_id']}, {c['action'].replace('_', ' ')}{target}** "
                    f"({c['doc_id']} p.{c['page']})")
        st.caption(c["source_text"])
        if not c["applied"]:
            st.warning(f"Not applied: {c['note'] or 'the instruction could not be applied'}")
        if c["action"] == "revise_date":
            st.markdown(f"New date: **{c['new_text']}**")
        elif c["target_paragraph"]:
            before, after = st.columns(2)
            before.markdown("**Before**")
            for b in c["before"] or [{"text": "(no earlier text found)", "doc_id": "-", "page": "-"}]:
                before.markdown(f"> {b['text']}  \n({b['doc_id']} p.{b['page']})")
            after.markdown("**After**")
            for b in c["after"] or [{"text": c["after_placeholder"], "doc_id": "-", "page": "-"}]:
                after.markdown(f"> {b['text']}  \n({b['doc_id']} p.{b['page']})")
            for i in c["items"]:
                st.markdown(f"- `{i['req_id']}` {i['source_text']} ({i['status_label']})")
