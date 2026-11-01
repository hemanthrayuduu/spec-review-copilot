"""The source viewer: the rendered page with the requirement highlighted, and its evidence (spec 8.15)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # app/ on the path, whether run alone or by the shell

import streamlit as st  # noqa: E402

from api_client import ApiError  # noqa: E402
from views.common import context, show_error  # noqa: E402

api, run_id, _ = context()
try:
    items = api.items(run_id)
except ApiError as exc:
    show_error(exc)
    st.stop()
st.header("Source viewer")
if not items:
    st.info("This run has no requirements.")
    st.stop()
ids = [i["req_id"] for i in items]
pos = min(st.session_state.get("src_pos", 0), len(ids) - 1)
prev, nxt, _ = st.columns([1, 1, 6])
if prev.button("Previous", key="src_prev", disabled=pos == 0):
    pos -= 1
if nxt.button("Next", key="src_next", disabled=pos == len(ids) - 1):
    pos += 1
labels = {i["req_id"]: f"[{i['code'] or '-'}] {i['section_number'] or '-'} {i['paragraph_path']}: "
                       f"{i['source_text'][:90]}" for i in items}
chosen = st.selectbox("Requirement", ids, index=pos, format_func=labels.__getitem__, key=f"src_req_{pos}")
st.session_state["src_pos"] = ids.index(chosen)
item = items[ids.index(chosen)]
left, right = st.columns([3, 2])
with left:
    try:
        st.image(api.page_png(run_id, item["doc_id"], item["page"], item["req_id"]),
                 caption=f"{item['doc_id']} page {item['page']}", use_container_width=True)
    except ApiError as exc:
        show_error(exc)
with right:
    st.markdown(f"**{item['status_label']}**")
    st.write(item["source_text"])
    st.markdown(f"**Reason:** {item['ai_reason'] or '-'}")
    for e in item["evidence"]:
        tag = " · **SYNTHETIC**" if e["origin"] == "synthetic" else ""
        st.markdown(f"- `{e['evidence_id']}` ({e['ref']} p.{e['page'] or '-'}){tag}: {e['text'][:200]}")
