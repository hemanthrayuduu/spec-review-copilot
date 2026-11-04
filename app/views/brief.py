"""The triage brief: relevant sections, deadlines, forms, red flags, permit limits, and addenda, with pages."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # app/ on the path, whether run alone or by the shell

import streamlit as st  # noqa: E402

from api_client import ApiError  # noqa: E402
from views.common import STATUSES, context, md, show_error, show_groups  # noqa: E402,F401

api, run_id, _ = context()
try:
    brief = api.stage(run_id, "brief")
    items = api.items(run_id)
    groups = api.groups()
except ApiError as exc:
    show_error(exc)
    st.stop()
st.header(f"Brief: {md(brief['package_id'])}")
reviewed = sum(i["reviewed"] for i in items)
cols = st.columns(4)
cols[0].metric("Requirements", len(items))
cols[1].metric("Reviewed", reviewed)
cols[2].metric("Deviations", sum(i["final_status"] == "deviation" for i in items))
cols[3].metric("Need an engineer", sum(i["final_status"] == "needs_engineer" for i in items))
st.subheader("Requirements by group")
show_groups(items, groups)


def cited(rows: list[dict], title: str) -> None:
    st.subheader(title)
    if not rows:
        st.write("None found.")
    for r in rows:
        superseded = f" ~~superseded by {md(r['superseded_by'])}~~" if r.get("superseded_by") else ""
        st.markdown(f"- {md(r['text'])} ({md(r['doc_id'])} p.{r['page']}){superseded}")


st.subheader("Relevant sections")
st.dataframe([{"Section": s.get("number") or "-", "Title": s["title"], "Doc": s["doc_id"],
               "Pages": f"{s['page_start']}-{s['page_end']}", "Product line": s.get("product_line") or "-"}
              for s in brief["relevant_sections"]], hide_index=True, use_container_width=True)
cited(brief["deadlines"], "Deadlines")
cited(brief["required_forms"], "Required forms")
cited(brief["red_flags"], "Red flags")
cited(brief["addenda_changes"], "Addenda changes")
st.subheader("Permit limits")
st.dataframe([{"Parameter": p["parameter"], "Limit": p["limit_type"], "Value": p["value"], "Unit": p["unit"],
               "Page": f"{p['doc_id']} p.{p['page']}"} for p in brief["permit_limits"]], hide_index=True)
