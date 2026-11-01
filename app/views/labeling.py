"""The labeling helper (spec 8.15): the owner adds golden labels by hand, page by page. Local only.

Every field starts blank. Nothing here reads pipeline output or calls a language model.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from spec_review.config import get_settings  # noqa: E402
from spec_review.eval.golden import GoldenRequirement  # noqa: E402
from spec_review.ingest import doc_id_for, package_pdfs  # noqa: E402
from spec_review.labeling import add_requirement, blank_row, load_labels, page_count, page_view  # noqa: E402
from spec_review.labeling import remove_requirement  # noqa: E402
from spec_review.models import Category, Operator  # noqa: E402
from views.common import md  # noqa: E402

CATEGORIES = list(Category.__args__)  # type: ignore[attr-defined]
OPERATORS = ["", *Operator.__args__]  # type: ignore[attr-defined]

st.header("Labeling helper")
st.caption("For the owner: write golden labels by hand. Fields start blank and are never prefilled.")
root = Path(st.session_state.get("labeling_root") or get_settings().raw_dir)
golden_root = Path(st.session_state.get("labeling_golden") or get_settings().golden_dir)
splits = sorted(p.name for p in root.iterdir() if p.is_dir()) if root.is_dir() else []
if not splits:
    st.info(f"No package folders under {md(root)}.")
    st.stop()
split = st.selectbox("Split", splits, key="lab_split")
packages = sorted(p.name for p in (root / split).iterdir() if p.is_dir())
package = st.selectbox("Package", packages, key="lab_package")
if not package:
    st.stop()
package_dir = root / split / package
pdfs = package_pdfs(package_dir)  # the files ingest reads, so labels use its document ids
if not pdfs:
    st.info(f"{md(split)}/{md(package)} has no PDF files to label.")
    st.stop()
pdf = st.selectbox("Document", pdfs, format_func=lambda p: doc_id_for(package_dir, p), key="lab_doc")
doc_id = doc_id_for(package_dir, pdf)
page = int(st.number_input("Page", min_value=1, value=1, step=1, key="lab_page"))
pages = page_count(pdf)
if page > pages:
    st.warning(f"{md(doc_id)} has {pages} page{'s' if pages != 1 else ''}; pick a page from 1 to {pages}.")
    st.stop()
png, text = page_view(pdf, page)
left, right = st.columns([3, 2])
left.image(png, caption=f"{doc_id} page {page}", use_container_width=True)
with left.expander("Page text"):
    st.text(text)

golden_path = golden_root / split / f"{package}.json"
row = blank_row(doc_id, page)
with right.form("lab_form", clear_on_submit=True):
    section = st.text_input("Section number", key="lab_section")
    path = st.text_input("Paragraph path", key="lab_path")
    source = st.text_area("Source text (copy exactly)", key="lab_source")
    category = st.selectbox("Category", CATEGORIES, index=None, key="lab_category")
    parameter = st.text_input("Parameter", key="lab_parameter")
    operator = st.selectbox("Operator", OPERATORS, key="lab_operator")
    value = st.text_input("Value", key="lab_value")
    unit = st.text_input("Unit", key="lab_unit")
    mandatory = st.radio("Mandatory", ["yes", "no"], index=None, horizontal=True, key="lab_mandatory")
    if st.form_submit_button("Add requirement"):
        row.update(section_number=section or None, paragraph_path=path, source_text=source, category=category,
                   parameter=parameter or None, operator=operator or None, value=value or None, unit=unit or None,
                   mandatory=None if mandatory is None else mandatory == "yes")
        try:
            add_requirement(golden_path, package, GoldenRequirement(**row))
            st.success(f"Added to {md(golden_path)}")
        except ValidationError as exc:
            st.error(f"Not saved: {md(exc.errors()[0]['loc'][0])} {md(exc.errors()[0]['msg'])}")
        except ValueError as exc:
            st.error(f"Not saved: {md(exc)}")

labels = load_labels(golden_path, package)
st.subheader(f"{len(labels.requirements)} labels in {md(golden_path.name)}")
for n, r in enumerate(labels.requirements):
    a, b = st.columns([8, 1])
    a.markdown(md(f"{r.doc_id} p.{r.page} · {r.section_number or '-'} {r.paragraph_path}: {r.source_text[:100]}"))
    if b.button("Delete", key=f"lab_del_{n}", disabled=bool(labels.traps)):
        remove_requirement(golden_path, n)
        st.rerun()
