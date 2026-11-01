"""The checklist: every requirement, its AI status and evidence, and the engineer's decision (spec 8.15)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # app/ on the path, whether run alone or by the shell

import streamlit as st  # noqa: E402

from api_client import ApiError  # noqa: E402
from views.common import STATUSES, context, show_error  # noqa: E402,F401

api, run_id, reviewer = context()
try:
    items = api.items(run_id)
except ApiError as exc:
    show_error(exc)
    st.stop()
st.header("Checklist")
f1, f2, f3, f4 = st.columns(4)
statuses = f1.multiselect("Status", sorted({i["final_status"] or "not matched" for i in items}), key="cl_status")
categories = f2.multiselect("Category", sorted({i["category"] for i in items}), key="cl_category")
sections = f3.multiselect("Section", sorted({i["section_number"] or "-" for i in items}), key="cl_section")
only_open = f4.checkbox("Only unreviewed", key="cl_open")
shown = [i for i in items
         if (not statuses or (i["final_status"] or "not matched") in statuses)
         and (not categories or i["category"] in categories)
         and (not sections or (i["section_number"] or "-") in sections)
         and (not only_open or not i["reviewed"])]
st.caption(f"{len(shown)} of {len(items)} shown, {sum(i['reviewed'] for i in items)} reviewed")
st.dataframe([{"Code": i["code"], "Status": i["status_label"], "Section": i["section_number"] or "-",
               "Paragraph": i["paragraph_path"], "Page": f"{i['doc_id']} p.{i['page']}",
               "Requirement": i["source_text"], "Synthetic": "SYNTHETIC" if i["uses_synthetic"] else ""}
              for i in shown], hide_index=True, use_container_width=True)

if not reviewer:
    st.warning("Enter your name as Reviewer in the sidebar to save decisions.")
if shown and st.button(f"Approve all shown ({sum(not i['reviewed'] and bool(i['ai_status']) for i in shown)} "
                       "unreviewed, AI status as is)", key="cl_approve_all", disabled=not reviewer):
    for i in shown:
        if not i["reviewed"] and i["ai_status"]:
            api.decide(run_id, i["req_id"], i["ai_status"], "", reviewer)
    st.rerun()

if not shown:
    st.stop()
labels = {i["req_id"]: f"[{i['code'] or '-'}] {i['section_number'] or '-'} {i['paragraph_path']}: "
                       f"{i['source_text'][:90]}" for i in shown}
req_id = st.selectbox("Requirement", list(labels), format_func=labels.__getitem__, key="cl_req")
item = next(i for i in shown if i["req_id"] == req_id)
left, right = st.columns([3, 2])
with left:
    st.markdown(f"**{item['section_number'] or '-'} {item['paragraph_path']}** ({item['doc_id']} p.{item['page']})")
    st.write(item["source_text"])
    st.markdown(f"**AI status:** {item['ai_status'] or 'not matched'}  \n**Reason:** {item['ai_reason'] or '-'}")
    for e in item["evidence"]:
        tag = " · **SYNTHETIC**" if e["origin"] == "synthetic" else ""
        st.markdown(f"- `{e['evidence_id']}` ({e['basis'] or '-'}, {e['ref']} p.{e['page'] or '-'}){tag}: "
                    f"{e['text'][:200]}")
with right:
    default = item["final_status"] or "needs_engineer"
    status = st.selectbox("Final status", STATUSES, index=STATUSES.index(default), key=f"cl_final_{req_id}")
    note = st.text_area("Note (goes into the letter or the questions)", item["note"], key=f"cl_note_{req_id}")
    if st.button("Approve", key="cl_approve", disabled=not reviewer, type="primary"):
        try:
            api.decide(run_id, req_id, status, note, reviewer)
            st.rerun()
        except ApiError as exc:
            show_error(exc)
    if item["reviewed"]:
        st.caption(f"Reviewed by {item['reviewer']}: {item['final_status']}")
