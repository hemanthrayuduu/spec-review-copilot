"""What every review page needs: the API client, the open run, and the reviewer, from the session."""

import re
from collections.abc import Mapping
from typing import Any

import streamlit as st

from api_client import ApiClient, ApiError

STATUSES = ("comply", "comply_with_clarification", "deviation", "needs_engineer", "not_applicable")
_MARKDOWN = re.compile(r"([\\`*_{}\[\]()#+\-.!|~<>$:&])")


def md(text: object) -> str:
    """Untrusted text (PDF lines, AI reasons, notes, file names) shown literally inside Markdown.

    Every Markdown character is escaped, so "$500 ... $1,500" is not math and [x](url) is not a link or an image.
    """
    return _MARKDOWN.sub(r"\\\1", str(text))


def context(need_run: bool = True) -> tuple[ApiClient, str, str]:
    api = st.session_state.get("api")
    if api is None:
        st.info("Open the app with `uv run streamlit run app/streamlit_app.py` so it can reach the API.")
        st.stop()
    run_id = st.session_state.get("run_id") or ""
    if need_run and not run_id:
        st.info("Pick a run in the sidebar, or start one on the Run a package page.")
        st.stop()
    return api, run_id, st.session_state.get("reviewer") or ""


def show_error(exc: ApiError) -> None:
    st.error(exc.detail if exc.status == 0 else f"The API said: {md(exc)}")  # status 0 is our own message



def item_label(item: Mapping[str, Any]) -> str:
    """The checklist picker's line: where the item is, its parameter and value, then the sentence. Two values
    from one sentence, like a pump's flow and head, would otherwise look the same."""
    what = " ".join(str(x) for x in (item.get("parameter"), item.get("value"), item.get("unit")) if x)
    where = f"[{item['code'] or '-'}] {item['section_number'] or '-'} {item['paragraph_path']}: "
    return where + (f"{what} · " if what else "") + item["source_text"][:90]
