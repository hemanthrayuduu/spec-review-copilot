"""The labeling helper (spec 8.15): the owner adds golden labels by hand, page by page. Local only.

Every field starts blank. Nothing here reads pipeline output or calls a language model.
"""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402
from pydantic import BaseModel, ValidationError  # noqa: E402

from spec_review.config import get_settings  # noqa: E402
from spec_review.eval.golden import GoldenRequirement, GoldenSection  # noqa: E402
from spec_review.ingest import doc_id_for, package_pdfs  # noqa: E402
from spec_review.labeling import (  # noqa: E402
    LabelKind,
    add_label,
    blank_item,
    blank_row,
    blank_section,
    load_labels,
    page_count,
    page_view,
    remove_label,
)
from spec_review.models import BriefItem, Category, Operator  # noqa: E402
from views.common import md  # noqa: E402

CATEGORIES = list(Category.__args__)  # type: ignore[attr-defined]
OPERATORS = ["", *Operator.__args__]  # type: ignore[attr-defined]
# Each form's fields and their blank values. A good save sets them, never deletes them: only a value the page
# sets reaches the browser, which otherwise keeps showing what was typed. A refused save leaves them as typed.
BLANK: dict[LabelKind, dict[str, Any]] = {
    "requirements": {"lab_section": "", "lab_path": "", "lab_source": "", "lab_category": None, "lab_parameter": "",
                     "lab_operator": "", "lab_value": "", "lab_unit": "", "lab_mandatory": None, "lab_addendum": ""},
    "relevant_sections": {"lab_sec_number": "", "lab_sec_title": ""},  # its page fields go back to the page shown
    "deadlines": {"lab_dl_text": "", "lab_dl_section": ""},
    "required_forms": {"lab_form_text": "", "lab_form_section": ""},
}
SECTION_PAGES = ("lab_sec_first", "lab_sec_last")
NOUNS: dict[LabelKind, str] = {"requirements": "requirement", "relevant_sections": "relevant section",
                               "deadlines": "deadline", "required_forms": "required form"}

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
if note := st.session_state.pop("lab_saved", None):
    right.success(note)


def save(kind: LabelKind, model: type[BaseModel], data: dict[str, Any]) -> None:
    """Add one label. A refused save keeps the form as typed; a good one clears it."""
    try:
        add_label(golden_path, package, kind, model(**data))
    except ValidationError as exc:
        err = exc.errors()[0]
        st.error(f"Not saved: {md(err['loc'][0] if err['loc'] else '')} {md(err['msg'])}")
    except (TypeError, ValueError) as exc:  # ValueError: a generated, frozen golden file
        st.error(f"Not saved: {md(exc)}")
    else:
        st.session_state["lab_reset"] = [kind]
        st.session_state["lab_saved"] = f"Added a {NOUNS[kind]} to {md(golden_path)}"
        st.rerun()


for done in st.session_state.pop("lab_reset", []):
    st.session_state.update(BLANK[done] | ({key: page for key in SECTION_PAGES} if done == "relevant_sections" else {}))
for key in SECTION_PAGES:
    st.session_state.setdefault(key, page)
# Keyed, so a save that adds a message above the tabs still shows the tab the owner was working in.
req_tab, sec_tab, dl_tab, form_tab = right.tabs(["Requirement", "Relevant section", "Deadline", "Required form"],
                                                key="lab_tab", on_change="rerun")
with req_tab.form("lab_form"):
    section = st.text_input("Section number", key="lab_section")
    path = st.text_input("Paragraph path", key="lab_path")
    source = st.text_area("Source text (copy exactly)", key="lab_source")
    category = st.selectbox("Category", CATEGORIES, index=None, key="lab_category")
    parameter = st.text_input("Parameter", key="lab_parameter")
    operator = st.selectbox("Operator", OPERATORS, key="lab_operator")
    value = st.text_input("Value", key="lab_value")
    unit = st.text_input("Unit", key="lab_unit")
    mandatory = st.radio("Mandatory", ["yes", "no"], index=None, horizontal=True, key="lab_mandatory")
    addendum = st.text_input("From addendum", key="lab_addendum",
                             help="Only for a requirement an addendum changed: label it once, in its final form, "
                                  "and name the addendum, for example Addendum 2.")
    if st.form_submit_button("Add requirement", key="lab_add_req"):
        save("requirements", GoldenRequirement, blank_row(doc_id, page) | {
            "section_number": section or None, "paragraph_path": path, "source_text": source, "category": category,
            "parameter": parameter or None, "operator": operator or None, "value": value or None,
            "unit": unit or None, "mandatory": None if mandatory is None else mandatory == "yes",
            "from_addendum": addendum or None})
with sec_tab.form("lab_sec_form"):
    number = st.text_input("Section number (blank if unnumbered)", key="lab_sec_number")
    title = st.text_input("Title", key="lab_sec_title")
    first = int(st.number_input("First page", min_value=1, step=1, key="lab_sec_first"))
    last = int(st.number_input("Last page", min_value=1, step=1, key="lab_sec_last"))
    if st.form_submit_button("Add relevant section", key="lab_add_sec"):
        if not first <= last <= pages:
            st.error(f"Not saved: the first page must come before the last, and both within 1 to {pages}.")
        else:
            save("relevant_sections", GoldenSection, blank_section(doc_id, page) | {
                "number": number or None, "title": title, "page_start": first, "page_end": last})
with dl_tab.form("lab_dl_form"):
    dl_text = st.text_area("Deadline text (copy exactly)", key="lab_dl_text")
    dl_section = st.text_input("Section number", key="lab_dl_section")
    if st.form_submit_button("Add deadline", key="lab_add_dl"):
        save("deadlines", BriefItem, blank_item(doc_id, page) | {"text": dl_text, "section_number": dl_section or None})
with form_tab.form("lab_form_form"):
    form_text = st.text_area("Form title or line (copy exactly)", key="lab_form_text")
    form_section = st.text_input("Section number", key="lab_form_section")
    if st.form_submit_button("Add required form", key="lab_add_form"):
        save("required_forms", BriefItem, blank_item(doc_id, page) | {
            "text": form_text, "section_number": form_section or None})


def describe(kind: LabelKind, r: Any) -> str:
    if kind == "relevant_sections":
        return f"{r.doc_id} p.{r.page_start}-{r.page_end} · {r.number or '-'} {r.title}"
    if kind == "requirements":
        added = f" · from {r.from_addendum}" if r.from_addendum else ""
        return f"{r.doc_id} p.{r.page} · {r.section_number or '-'} {r.paragraph_path}: {r.source_text[:100]}{added}"
    return f"{r.doc_id} p.{r.page} · {r.section_number or '-'}: {r.text[:100]}"


labels = load_labels(golden_path, package)
counts = [(kind, noun, len(getattr(labels, kind))) for kind, noun in NOUNS.items()]
st.subheader(", ".join(f"{n} {noun}{'' if n == 1 else 's'}" for _, noun, n in counts) + f" in {md(golden_path.name)}")
for kind, noun, n in counts:
    with st.expander(f"{noun.capitalize()}s ({n})"):
        for i, r in enumerate(getattr(labels, kind)):
            a, b = st.columns([8, 1])
            a.markdown(md(describe(kind, r)))
            if b.button("Delete", key=f"lab_del_{kind}_{i}", disabled=bool(labels.traps)):
                remove_label(golden_path, kind, i)
                st.rerun()
