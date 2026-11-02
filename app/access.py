"""Who may use the review app (Phase 4). Locally, everyone. Hosted, only the emails the owner allowed.

Hosted on Azure Container Apps, the platform's own sign-in runs before any request reaches the app and passes
the signed-in account in the X-MS-CLIENT-PRINCIPAL-NAME header, so the app only compares that email with
ALLOWED_USERS. That header is trustworthy only when the platform requires sign-in for every request.
"""

from collections.abc import Mapping
from typing import NamedTuple

PRINCIPAL_HEADER = "X-MS-CLIENT-PRINCIPAL-NAME"
SIGN_IN_REQUIRED = "Sign in is required. Open the app's address again to sign in."


class PageSpec(NamedTuple):
    path: str
    title: str
    icon: str
    default: bool = False


PAGES = (PageSpec("views/run.py", "Run a package", "▶️"),
         PageSpec("views/brief.py", "Brief", "📋", default=True),
         PageSpec("views/checklist.py", "Checklist", "✅"),
         PageSpec("views/source.py", "Source viewer", "📄"),
         PageSpec("views/addenda.py", "Addenda changes", "📝"),
         PageSpec("views/outputs.py", "Outputs", "📦"),
         PageSpec("views/labeling.py", "Labeling helper (local)", "🏷️"))
LOCAL_ONLY = {"views/labeling.py"}  # writes golden labels on this machine; never part of the hosted app


def allowlist(value: str) -> set[str]:
    return {email.strip().lower() for email in value.replace(";", ",").split(",") if email.strip()}


def access(headers: Mapping[str, str], hosted: bool, allowed: str) -> tuple[bool, str]:
    """(may use the app, the signed-in email or why not)."""
    if not hosted:
        return True, ""
    email = next((v for k, v in headers.items() if k.lower() == PRINCIPAL_HEADER.lower()), "").strip().lower()
    if not email:
        return False, SIGN_IN_REQUIRED
    if email not in allowlist(allowed):
        return False, f"You are signed in as {email}. Ask the owner for access."
    return True, email


def page_specs(hosted: bool) -> list[PageSpec]:
    return [p for p in PAGES if not (hosted and p.path in LOCAL_ONLY)]
