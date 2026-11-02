"""Host the review app on Azure Container Apps (Phase 4): a private registry, a file share, the API, the app.

    AZURE_SUBSCRIPTION_ID=<id> uv run python scripts/deploy_azure.py --allow you@example.edu [step ...]

Steps, in order (default: all): base, image, api, app. Each step can be rerun; what exists is kept.
  base   resource group, registry (Basic), pull identity, storage account and share, Container Apps environment
  image  builds the image for linux/amd64 from the current commit and pushes it to the private registry
  api    the API: internal ingress only, keys from .env as Container Apps secrets, runs/ and uploads on the share
  app    the review app: public, Microsoft sign-in required (Easy Auth), only the --allow emails get in

The image carries the cached Lakeview replies and public brochure pages, so the registry stays private.
Nothing secret is printed: keys travel in a spec file only this user can read, deleted right after use.
Grant or remove access later with scripts/grant_access.sh.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, get_args

from pydantic import SecretStr

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from spec_review.config import Settings  # noqa: E402

LOCATION = "germanywestcentral"
RG = os.environ.get("RESOURCE_GROUP", "rg-specreview-demo-gwc")
ACR = os.environ.get("ACR_NAME", "acrspecreviewdemo")
STORAGE = os.environ.get("STORAGE_ACCOUNT", "stspecreviewdemo")
SHARE = "specreview"
ENV_NAME = "cae-specreview-demo-gwc"
API = "ca-specreview-api"
APP = os.environ.get("APP_NAME", "ca-specreview-app")
IDENTITY = "id-specreview-pull"
REPOSITORY = "spec-review-copilot"
SIGN_IN_NAME = "Spec Review Copilot (demo)"
AUTH_SECRET = "microsoft-provider-authentication-secret"
UPLOAD_CAP_MB = 25
APP_UID = 1000  # the image's app user
STEPS = ("base", "image", "api", "app")


# ---- what goes to the cloud (pure, tested) ----

def _is_path(annotation: Any) -> bool:
    return annotation is Path or Path in get_args(annotation)


def api_environment(dotenv: Mapping[str, str | None]) -> tuple[dict[str, str], list[dict[str, str]]]:
    """(secrets by secret name, the API container's env). Keys become secrets; local paths, names Settings does
    not know, and blanks stay on this machine; uploads are capped for the hosted copy."""
    fields = Settings.model_fields
    secrets: dict[str, str] = {}
    env: list[dict[str, str]] = []
    for name, value in dotenv.items():
        field = fields.get(name.lower())
        if field is None or not value or _is_path(field.annotation) or name == "MAX_UPLOAD_MB":
            continue
        if field.annotation is SecretStr:
            ref = name.lower().replace("_", "-")
            secrets[ref] = value
            env.append({"name": name, "secretRef": ref})
        else:
            env.append({"name": name, "value": value})
    env.append({"name": "MAX_UPLOAD_MB", "value": str(UPLOAD_CAP_MB)})
    return secrets, env


def _registry(image: str, identity_id: str) -> list[dict[str, str]]:
    return [{"server": image.split("/", 1)[0], "identity": identity_id}]


def _identity(identity_id: str) -> dict[str, Any]:
    return {"type": "UserAssigned", "userAssignedIdentities": {identity_id: {}}}


def api_spec(*, env_id: str, image: str, identity_id: str, secrets: Mapping[str, str],
             env: list[dict[str, str]]) -> dict[str, Any]:
    options = f"uid={APP_UID},gid={APP_UID},dir_mode=0750,file_mode=0640,mfsymlinks,nobrl"
    return {
        "location": LOCATION,
        "identity": _identity(identity_id),
        "properties": {
            "managedEnvironmentId": env_id,
            "configuration": {
                "activeRevisionsMode": "Single",
                "ingress": {"external": False, "targetPort": 8000, "transport": "http", "allowInsecure": False},
                "registries": _registry(image, identity_id),
                "secrets": [{"name": k, "value": v} for k, v in secrets.items()],
            },
            "template": {
                "containers": [{
                    "name": "api", "image": image,
                    "command": ["specreview", "serve", "--host", "0.0.0.0", "--port", "8000"],
                    "env": env,
                    "resources": {"cpu": 1.0, "memory": "2Gi"},
                    "volumeMounts": [{"volumeName": "data", "mountPath": "/app/runs", "subPath": "runs"},
                                     {"volumeName": "data", "mountPath": "/app/data/uploads", "subPath": "uploads"}],
                }],
                "scale": {"minReplicas": 0, "maxReplicas": 1},
                "volumes": [{"name": "data", "storageType": "AzureFile", "storageName": SHARE,
                             "mountOptions": options}],
            },
        },
    }


def app_spec(*, env_id: str, image: str, identity_id: str, api_url: str, allowed: Sequence[str],
             auth_secret: str) -> dict[str, Any]:
    command = ["streamlit", "run", "app/streamlit_app.py", "--server.headless", "true", "--server.address", "0.0.0.0",
               "--server.port", "8501", "--browser.gatherUsageStats", "false",
               "--server.maxUploadSize", str(UPLOAD_CAP_MB)]
    return {
        "location": LOCATION,
        "identity": _identity(identity_id),
        "properties": {
            "managedEnvironmentId": env_id,
            "configuration": {
                "activeRevisionsMode": "Single",
                "ingress": {"external": True, "targetPort": 8501, "transport": "auto", "allowInsecure": False},
                "registries": _registry(image, identity_id),
                "secrets": [{"name": AUTH_SECRET, "value": auth_secret}],
            },
            "template": {
                "containers": [{
                    "name": "app", "image": image, "command": command,
                    "env": [{"name": "HOSTED", "value": "1"},
                            {"name": "ALLOWED_USERS", "value": ",".join(e.strip().lower() for e in allowed)},
                            {"name": "API_URL", "value": api_url}],
                    "resources": {"cpu": 0.5, "memory": "1Gi"},
                }],
                "scale": {"minReplicas": 0, "maxReplicas": 1},
            },
        },
    }


def environment_create_args() -> list[str]:
    """Workload-profiles mode with only the Consumption profile: no fixed fee, and unlike the Express mode the
    preview CLI picks by default, it can mount the file share."""
    return ["containerapp", "env", "create", "-n", ENV_NAME, "-g", RG, "-l", LOCATION,
            "--environment-mode", "WorkloadProfiles", "--logs-destination", "none"]


def write_spec(spec: Mapping[str, Any], folder: Path) -> Path:
    """The spec as YAML (JSON is YAML), readable only by this user because it may hold keys."""
    fd, name = tempfile.mkstemp(suffix=".yaml", dir=folder)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, "w") as handle:
        json.dump(spec, handle)
    return Path(name)


def image_tag(*, status: str, sha: str) -> str:
    """The commit the image is built from; uncommitted changes to tracked files would not match it."""
    if status.strip():
        raise SystemExit("Commit or stash your changes first, so the image matches a commit.")
    return sha


# ---- Azure CLI calls ----

def az(*args: str, check: bool = True, subscription: bool = True) -> str | None:
    """The command's output; on failure, stop with Azure's error (check) or return None."""
    cmd = ["az", *args, "--only-show-errors"] + (["--subscription", SUB] if subscription else [])
    done = subprocess.run(cmd, capture_output=True, text=True)
    if done.returncode:
        if check:
            raise SystemExit(f"az {' '.join(args[:3])} failed:\n{done.stderr.strip()[-1500:]}")
        return None
    return done.stdout.strip()


def out(*args: str, subscription: bool = True) -> str:
    return az(*args, subscription=subscription) or ""


def exists(*args: str) -> bool:
    return bool(az(*args, "--query", "id", "-o", "tsv", check=False))


def step(text: str) -> None:
    print(f"- {text}", flush=True)


def base() -> None:
    if not exists("group", "show", "-n", RG):
        step(f"resource group {RG}")
        az("group", "create", "-n", RG, "-l", LOCATION, "-o", "none")
    if not exists("acr", "show", "-n", ACR, "-g", RG):
        step(f"private registry {ACR} (Basic, no admin user)")
        az("acr", "create", "-n", ACR, "-g", RG, "-l", LOCATION, "--sku", "Basic", "--admin-enabled", "false",
           "-o", "none")
    if not exists("identity", "show", "-n", IDENTITY, "-g", RG):
        step(f"pull identity {IDENTITY} with AcrPull on {ACR}")
        principal = out("identity", "create", "-n", IDENTITY, "-g", RG, "-l", LOCATION,
                        "--query", "principalId", "-o", "tsv")
        acr_id = out("acr", "show", "-n", ACR, "-g", RG, "--query", "id", "-o", "tsv")
        for attempt in range(1, 7):  # a new identity takes a moment to reach the directory
            if az("role", "assignment", "create", "--assignee-object-id", principal, "--assignee-principal-type",
                  "ServicePrincipal", "--role", "AcrPull", "--scope", acr_id, "-o", "none",
                  check=attempt == 6) is not None:
                break
            time.sleep(10)
    if not exists("storage", "account", "show", "-n", STORAGE, "-g", RG):
        step(f"storage account {STORAGE} (Standard LRS, HTTPS only, TLS 1.2, no public blobs)")
        az("storage", "account", "create", "-n", STORAGE, "-g", RG, "-l", LOCATION, "--sku", "Standard_LRS",
           "--kind", "StorageV2", "--https-only", "true", "--min-tls-version", "TLS1_2",
           "--allow-blob-public-access", "false", "-o", "none")
    key = out("storage", "account", "keys", "list", "-n", STORAGE, "-g", RG, "--query", "[0].value", "-o", "tsv")
    if out("storage", "share-rm", "exists", "--storage-account", STORAGE, "-g", RG, "-n", SHARE,
           "--query", "exists", "-o", "tsv") != "true":
        step(f"file share {SHARE} (5 GiB quota) with runs/ and uploads/")
        az("storage", "share-rm", "create", "--storage-account", STORAGE, "-g", RG, "-n", SHARE, "--quota", "5",
           "-o", "none")
    for folder in ("runs", "uploads"):
        az("storage", "directory", "create", "--account-name", STORAGE, "--account-key", key, "--share-name", SHARE,
           "-n", folder, "-o", "none", subscription=False)
    if not exists("containerapp", "env", "show", "-n", ENV_NAME, "-g", RG):
        step(f"Container Apps environment {ENV_NAME} (consumption, no log workspace)")
        az(*environment_create_args(), "-o", "none")
    step(f"environment storage {SHARE} -> {STORAGE}/{SHARE}")
    az("containerapp", "env", "storage", "set", "-n", ENV_NAME, "-g", RG, "--storage-name", SHARE,
       "--azure-file-account-name", STORAGE, "--azure-file-account-key", key, "--azure-file-share-name", SHARE,
       "--access-mode", "ReadWrite", "-o", "none")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout


def image_ref() -> str:
    tag = image_tag(status=git("status", "--porcelain", "--untracked-files=no"),
                    sha=git("rev-parse", "--short", "HEAD").strip())
    return f"{ACR}.azurecr.io/{REPOSITORY}:{tag}"


def image() -> None:
    ref = image_ref()
    step(f"build {ref} for linux/amd64 and push it")
    az("acr", "login", "-n", ACR, "-o", "none")
    subprocess.run(["docker", "buildx", "build", "--platform", "linux/amd64", "--provenance=false", "--tag", ref,
                    "--push", "."], cwd=REPO_ROOT, check=True)


def _env_id() -> str:
    return out("containerapp", "env", "show", "-n", ENV_NAME, "-g", RG, "--query", "id", "-o", "tsv")


def _identity_id() -> str:
    return out("identity", "show", "-n", IDENTITY, "-g", RG, "--query", "id", "-o", "tsv")


def _create_or_update(name: str, spec: dict[str, Any]) -> None:
    if exists("containerapp", "show", "-n", name, "-g", RG):
        step(f"{name}: new image {spec['properties']['template']['containers'][0]['image']}")
        az("containerapp", "update", "-n", name, "-g", RG,
           "--image", spec["properties"]["template"]["containers"][0]["image"], "-o", "none")
        return
    with tempfile.TemporaryDirectory() as folder:
        path = write_spec(spec, Path(folder))
        step(f"{name}: create")
        az("containerapp", "create", "-n", name, "-g", RG, "--yaml", str(path), "-o", "none")


def api() -> None:
    from dotenv import dotenv_values

    secrets, env = api_environment(dotenv_values(REPO_ROOT / ".env"))
    step(f"{API}: {len(secrets)} keys as secrets, {len(env) - len(secrets)} plain settings")
    _create_or_update(API, api_spec(env_id=_env_id(), image=image_ref(), identity_id=_identity_id(),
                                    secrets=secrets, env=env))


def app(allowed: Sequence[str]) -> None:
    domain = out("containerapp", "env", "show", "-n", ENV_NAME, "-g", RG, "--query", "properties.defaultDomain",
                 "-o", "tsv")
    fqdn = f"{APP}.{domain}"
    client_id = _sign_in_registration(f"https://{fqdn}/.auth/login/aad/callback")
    created = not exists("containerapp", "show", "-n", APP, "-g", RG)
    secret = ""
    if created:  # a fresh client secret goes straight into the new app, never to the screen
        step(f"sign-in secret for {SIGN_IN_NAME} (1 year)")
        secret = out("ad", "app", "credential", "reset", "--id", client_id, "--display-name", "easyauth",
                     "--years", "1", "--query", "password", "-o", "tsv", subscription=False)
    _create_or_update(APP, app_spec(env_id=_env_id(), image=image_ref(), identity_id=_identity_id(),
                                    api_url=f"https://{API}.internal.{domain}", allowed=allowed,
                                    auth_secret=secret))
    step(f"{APP}: Microsoft sign-in required for every request")
    az("containerapp", "auth", "microsoft", "update", "-n", APP, "-g", RG, "--client-id", client_id,
       "--client-secret-name", AUTH_SECRET, "--issuer", "https://login.microsoftonline.com/common/v2.0",
       "--yes", "-o", "none")
    az("containerapp", "auth", "update", "-n", APP, "-g", RG, "--enabled", "true",
       "--unauthenticated-client-action", "RedirectToLoginPage", "--redirect-provider", "azureactivedirectory",
       "--require-https", "true", "-o", "none")
    print(f"\nThe app: https://{fqdn}\nAllowed: {', '.join(a.lower() for a in allowed)}")


def _sign_in_registration(redirect_uri: str) -> str:
    """The Entra app registration for Microsoft sign-in: work, school, and personal Microsoft accounts.
    Its audience and redirect address are set on every run, so a half-made or older registration is fixed too."""
    client_id = out("ad", "app", "list", "--display-name", SIGN_IN_NAME, "--query", "[0].appId", "-o", "tsv",
                    subscription=False)
    if not client_id:
        step(f"app registration {SIGN_IN_NAME!r} (any Microsoft account; the allowlist decides who gets in)")
        client_id = out("ad", "app", "create", "--display-name", SIGN_IN_NAME, "--sign-in-audience",
                        "AzureADMultipleOrgs", "--query", "appId", "-o", "tsv", subscription=False)
    body = {"signInAudience": "AzureADandPersonalMicrosoftAccount",
            "api": {"requestedAccessTokenVersion": 2},  # personal accounts need v2 tokens
            "web": {"redirectUris": [redirect_uri], "implicitGrantSettings": {"enableIdTokenIssuance": True}}}
    az("rest", "--method", "PATCH", "--url", f"https://graph.microsoft.com/v1.0/applications(appId='{client_id}')",
       "--body", json.dumps(body), subscription=False)
    return client_id


SUB = ""


def main(argv: Sequence[str] | None = None) -> None:
    global SUB
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("steps", nargs="*", metavar="step", help=f"any of {', '.join(STEPS)} (default: all)")
    parser.add_argument("--allow", action="append", default=[], help="an email that may use the app (repeatable)")
    args = parser.parse_args(argv)
    SUB = os.environ.get("AZURE_SUBSCRIPTION_ID", "")
    if not SUB:
        raise SystemExit("Set AZURE_SUBSCRIPTION_ID to the subscription that hosts the demo.")
    steps = args.steps or list(STEPS)
    if unknown := sorted(set(steps) - set(STEPS)):
        raise SystemExit(f"Unknown step {', '.join(unknown)}; the steps are {', '.join(STEPS)}.")
    if "app" in steps and not args.allow:
        raise SystemExit("Name at least one --allow email for the app.")
    for name in [s for s in STEPS if s in steps]:
        print(f"[{name}]", flush=True)
        if name == "app":
            app(args.allow)
        else:
            globals()[name]()


if __name__ == "__main__":
    main()
