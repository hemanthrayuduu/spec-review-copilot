"""The Azure deploy script's pure parts: which settings reach the cloud, and how (Phase 4 hosting)."""

import stat

import pytest

from scripts import deploy_azure as dz

DOTENV = {
    "PROVIDER_LLM": "azure",
    "AZURE_OPENAI_ENDPOINT": "https://example.invalid/",
    "AZURE_OPENAI_KEY": "sk-openai-123",
    "AZURE_SEARCH_KEY": "sk-search-456",
    "AZURE_DOCINTEL_KEY": "",
    "LLM_CACHE_DIR": "/Users/someone/.cache/llm",
    "RUNS_DIR": "/Users/someone/runs",
    "TESSDATA_PREFIX": "/opt/homebrew/share/tessdata",
    "MAX_UPLOAD_MB": "200",
}


def env_map(env: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {e["name"]: e for e in env}


def test_keys_go_in_as_secrets_and_never_as_plain_values() -> None:
    secrets, env = dz.api_environment(DOTENV)
    assert secrets == {"azure-openai-key": "sk-openai-123", "azure-search-key": "sk-search-456"}
    by_name = env_map(env)
    assert by_name["AZURE_OPENAI_KEY"] == {"name": "AZURE_OPENAI_KEY", "secretRef": "azure-openai-key"}
    assert all("value" not in e or e["value"] not in secrets.values() for e in env)


def test_local_paths_unknown_names_and_blanks_stay_on_this_machine() -> None:
    _, env = dz.api_environment(DOTENV)
    names = set(env_map(env))
    assert {"LLM_CACHE_DIR", "RUNS_DIR", "TESSDATA_PREFIX", "AZURE_DOCINTEL_KEY"}.isdisjoint(names)
    assert {"PROVIDER_LLM", "AZURE_OPENAI_ENDPOINT"} <= names


def test_hosted_upload_cap_replaces_the_local_one() -> None:
    _, env = dz.api_environment(DOTENV)
    assert [e for e in env if e["name"] == "MAX_UPLOAD_MB"] == [{"name": "MAX_UPLOAD_MB", "value": "25"}]


def test_api_is_internal_single_replica_and_keeps_runs_and_uploads_on_the_share() -> None:
    spec = dz.api_spec(env_id="/env", image="r.azurecr.io/x:abc", identity_id="/id", secrets={"k": "v"},
                       env=[{"name": "A", "value": "1"}])
    props = spec["properties"]
    assert props["configuration"]["ingress"]["external"] is False
    assert props["configuration"]["ingress"]["targetPort"] == 8000
    assert props["configuration"]["secrets"] == [{"name": "k", "value": "v"}]
    assert props["template"]["scale"] == {"minReplicas": 0, "maxReplicas": 1}  # one writer for reviews.sqlite
    mounts = {m["mountPath"]: m["subPath"] for m in props["template"]["containers"][0]["volumeMounts"]}
    assert mounts == {"/app/runs": "runs", "/app/data/uploads": "uploads"}
    options = props["template"]["volumes"][0]["mountOptions"].split(",")
    assert {"uid=1000", "gid=1000", "nobrl", "mfsymlinks"} <= set(options)  # app user; SQLite locks; runs/latest


def test_app_is_public_hosted_and_admits_only_the_allowed_emails() -> None:
    spec = dz.app_spec(env_id="/env", image="r.azurecr.io/x:abc", identity_id="/id",
                       api_url="https://ca-specreview-api.internal.example", allowed=["Owner@Example.edu"],
                       auth_secret="s3cret")
    props = spec["properties"]
    assert props["configuration"]["ingress"]["external"] is True
    assert props["configuration"]["ingress"]["targetPort"] == 8501
    assert props["configuration"]["secrets"] == [{"name": dz.AUTH_SECRET, "value": "s3cret"}]
    container = props["template"]["containers"][0]
    env = {e["name"]: e.get("value") for e in container["env"]}
    assert env == {"HOSTED": "1", "ALLOWED_USERS": "owner@example.edu",
                   "API_URL": "https://ca-specreview-api.internal.example"}
    assert container["command"][:3] == ["streamlit", "run", "app/streamlit_app.py"]
    assert "--server.maxUploadSize" in container["command"]
    assert "s3cret" not in str(container)


def test_both_apps_pull_with_the_managed_identity_not_a_password() -> None:
    for spec in (dz.api_spec(env_id="/env", image="r.azurecr.io/x:abc", identity_id="/id", secrets={}, env=[]),
                 dz.app_spec(env_id="/env", image="r.azurecr.io/x:abc", identity_id="/id", api_url="u",
                             allowed=["a@b.c"], auth_secret="s")):
        assert spec["identity"] == {"type": "UserAssigned", "userAssignedIdentities": {"/id": {}}}
        assert spec["properties"]["configuration"]["registries"] == [{"server": "r.azurecr.io", "identity": "/id"}]


def test_spec_file_is_readable_only_by_its_owner(tmp_path) -> None:
    path = dz.write_spec({"properties": {}}, tmp_path)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_image_tag_is_the_commit_and_refuses_uncommitted_changes() -> None:
    assert dz.image_tag(status="", sha="b05cc90") == "b05cc90"
    with pytest.raises(SystemExit, match="commit"):
        dz.image_tag(status=" M app/access.py\n", sha="b05cc90")


def test_environment_is_not_express_because_express_cannot_mount_the_share() -> None:
    args = dz.environment_create_args()
    assert args[args.index("--environment-mode") + 1] == "WorkloadProfiles"  # the preview CLI defaults to Express
    assert args[args.index("--logs-destination") + 1] == "none"
