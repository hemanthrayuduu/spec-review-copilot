"""The checklist: every requirement, its AI status and evidence, and the engineer's decision (spec 8.15)."""

import hashlib
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # app/ on the path, whether run alone or by the shell

import streamlit as st  # noqa: E402

from api_client import ApiError  # noqa: E402
from views.common import (EVIDENCE_FILTERS, STATUSES, context, evidence_kind,  # noqa: E402,F401
                          evidence_line, evidence_matches, flag_text, item_label, md, real_first, show_error,
                          show_groups, source_link)

BULK_STATUSES = ("comply", "comply_with_clarification", "not_applicable")

api, run_id, reviewer = context()
try:
    items = api.items(run_id)
    groups = api.groups()
except ApiError as exc:
    show_error(exc)
    st.stop()
st.header("Checklist")
show_groups(items, groups)

counts = Counter(i["group"] for i in items)
lines = {i["product_line"] or "General" for i in items}
f1, f2, f3, f4 = st.columns(4)
chosen = f1.multiselect("Group", [g["group"] for g in groups], format_func=lambda g: f"{g} ({counts[g]})",
                        key="cl_group")
statuses = f2.multiselect("Status", sorted({i["final_status"] or "not matched" for i in items}), key="cl_status")
equipment = f3.multiselect("Equipment", sorted(lines - {"General"}) + (["General"] if "General" in lines else []),
                           key="cl_equipment")
sections = f4.multiselect("Section", sorted({i["section_number"] or "-" for i in items}), key="cl_section")
e1, e2 = st.columns(2)
kind = e1.radio("Requirement", ["All", "Mandatory (shall)", "Preferred (should)"], horizontal=True,
                key="cl_mandatory")
by_evidence = {c: sum(evidence_matches(i, c) for i in items) for c in EVIDENCE_FILTERS}
evidence = e2.radio("Evidence behind the AI's decision", EVIDENCE_FILTERS, horizontal=True, key="cl_evidence",
                    format_func=lambda c: f"{c} ({by_evidence[c]})",
                    help="Real sources are public brochures and datasheets; synthetic rows are fictional demo data.")
k1, k2, k3 = st.columns(3)
flagged = k1.checkbox("Red flags only", key="cl_flagged")
changed = k2.checkbox("Changed by an addendum", key="cl_addendum")
only_open = k3.checkbox("Only unreviewed", key="cl_open")
shown = [i for i in items
         if (not chosen or i["group"] in chosen)
         and (not statuses or (i["final_status"] or "not matched") in statuses)
         and (not equipment or (i["product_line"] or "General") in equipment)
         and (not sections or (i["section_number"] or "-") in sections)
         and (kind == "All" or i["mandatory"] == (kind == "Mandatory (shall)"))
         and (not flagged or i["red_flags"])
         and (not changed or i["from_addendum"])
         and evidence_matches(i, evidence)
         and (not only_open or not i["reviewed"])]
st.caption(f"{len(shown)} of {len(items)} shown, {sum(i['reviewed'] for i in items)} reviewed")
st.dataframe([{"Code": i["code"], "Status": i["status_label"], "Group": i["group"],
               "Equipment": i["product_line"] or "General", "Section": i["section_number"] or "-",
               "Paragraph": i["paragraph_path"], "Page": source_link(run_id, i["req_id"], f"{i['doc_id']} p.{i['page']}"),
               "Requirement": i["source_text"], "Flags": flag_text(i), "Evidence": evidence_kind(i),
               "Synthetic": "SYNTHETIC" if i["uses_synthetic"] else ""}
              for i in shown], hide_index=True, use_container_width=True,
             column_config={"Page": st.column_config.LinkColumn("Page", display_text=r"cite=(.*)$",
                                                                  help="Open the page in the Source viewer")})

if not reviewer:
    st.warning("Enter your name as Reviewer in the sidebar to save decisions.")
# Bulk approval is for spot-checked routine items. Needs-engineer and deviation items are decided one by one.
bulk = [i for i in shown if not i["reviewed"] and i["ai_status"] in BULK_STATUSES]
if bulk:
    batch = hashlib.sha1("|".join(i["req_id"] for i in bulk).encode()).hexdigest()[:10]  # a new set needs a new tick
    confirmed = st.checkbox(f"I checked the {len(bulk)} unreviewed comply, clarification and not-applicable items "
                            "shown; approve them with their AI status", key=f"cl_approve_confirm_{batch}")
    if st.button(f"Approve all shown ({len(bulk)})", key="cl_approve_all", disabled=not (reviewer and confirmed)):
        saved = 0
        try:
            for i in bulk:
                api.decide(run_id, i["req_id"], i["ai_status"], "", reviewer)
                saved += 1
        except ApiError as exc:
            st.error(f"Saved {saved} of {len(bulk)}; the rest were not saved. {md(exc)}")
        else:
            st.rerun()

if not shown:
    st.stop()
labels = {i["req_id"]: item_label(i) for i in shown}
req_id = st.selectbox("Requirement", list(labels), format_func=labels.__getitem__, key="cl_req")
item = next(i for i in shown if i["req_id"] == req_id)
left, right = st.columns([3, 2])
with left:
    cite = f"{item['doc_id']} p.{item['page']}"
    st.markdown(f"**{md(item['section_number'] or '-')} {md(item['paragraph_path'])}** "
                f"([{md(cite)}]({source_link(run_id, item['req_id'], cite)}))")
    st.caption(f"{item['group']} · {item['category'].replace('_', ' ')} · "
               f"{'mandatory' if item['mandatory'] else 'preferred'}"
               + (f" · from {item['from_addendum']}" if item["from_addendum"] else "")
               + (f" · red flag: {flag_text(item)}" if item["red_flags"] else ""))
    st.markdown(md(item["source_text"]))
    st.markdown(f"**AI status:** {item['ai_status'] or 'not matched'}  \n**Reason:** {md(item['ai_reason'] or '-')}")
    for e in real_first(item["evidence"]):
        st.markdown(evidence_line(e))
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
        st.caption(f"Reviewed by {md(item['reviewer'])}: {item['final_status']}")
