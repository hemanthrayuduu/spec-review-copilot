"""The Azure deploy script's pure parts: which settings reach the cloud, and how (Phase 4 hosting)."""

import json
import stat
from pathlib import Path

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


def test_sign_in_registration_takes_any_microsoft_account_even_when_it_already_exists(monkeypatch) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_az(*args: str, check: bool = True, subscription: bool = True) -> str:
        calls.append(args)
        return "client-123" if args[:3] == ("ad", "app", "list") else ""

    monkeypatch.setattr(dz, "az", fake_az)
    assert dz._sign_in_registration("https://app.example/.auth/login/aad/callback") == "client-123"
    patch = [c for c in calls if c[:3] == ("rest", "--method", "PATCH")]
    assert len(patch) == 1
    body = json.loads(patch[0][patch[0].index("--body") + 1])
    assert body == {"signInAudience": "AzureADandPersonalMicrosoftAccount", "api": {"requestedAccessTokenVersion": 2},
                    "web": {"redirectUris": ["https://app.example/.auth/login/aad/callback"],
                            "implicitGrantSettings": {"enableIdTokenIssuance": True}}}
    assert "applications(appId='client-123')" in patch[0][patch[0].index("--url") + 1]


def test_a_named_tag_is_used_as_is_without_asking_git(monkeypatch) -> None:
    monkeypatch.setattr(dz, "git", lambda *a: pytest.fail("git was asked"))
    assert dz.image_ref("b4edfd4") == f"{dz.ACR}.azurecr.io/{dz.REPOSITORY}:b4edfd4"


def test_apps_are_not_pointed_at_an_image_the_registry_does_not_have(monkeypatch) -> None:
    monkeypatch.setattr(dz, "az", lambda *a, check=True, subscription=True: None)
    with pytest.raises(SystemExit, match="image step"):
        dz.require_image(f"{dz.ACR}.azurecr.io/{dz.REPOSITORY}:d2588fd")


class FakeAz:
    """Stands in for the Azure CLI in the app and api steps; records every call."""

    def __init__(self, exists: bool, allowed: str = "", fail: tuple[str, ...] = ()) -> None:
        self.exists, self.allowed, self.fail = exists, allowed, fail
        self.calls: list[tuple[str, ...]] = []
        self.specs: list[dict] = []

    def __call__(self, *args: str, check: bool = True, subscription: bool = True) -> str | None:
        self.calls.append(args)
        if self.fail and args[:len(self.fail)] == self.fail:
            if check:
                raise SystemExit("az failed")
            return None
        if args[:2] == ("containerapp", "show"):
            if args[args.index("--query") + 1] == "id":
                return "/app" if self.exists else None
            return self.allowed
        if args[:2] == ("containerapp", "create"):
            self.specs.append(json.loads(Path(args[args.index("--yaml") + 1]).read_text()))
            self.exists, self.allowed = True, allowed_in(self.specs[-1])
            return ""
        if args[:2] == ("containerapp", "update") and "--set-env-vars" in args:
            self.allowed = args[args.index("--set-env-vars") + 1].split("=", 1)[1]
            return ""
        return {("ad", "app"): "client-1", ("containerapp", "env"): "env.example"}.get(args[:2], "x")

    def index(self, *prefix: str) -> int:
        return next(i for i, c in enumerate(self.calls) if c[:len(prefix)] == prefix)


@pytest.fixture
def fake_az(monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    def make(**kw: object) -> FakeAz:
        fake = FakeAz(**kw)  # type: ignore[arg-type]
        monkeypatch.setattr(dz, "az", fake)
        monkeypatch.setattr(dz, "TAG", "abc1234")
        return fake
    return make


def allowed_in(spec: dict) -> str:
    env = spec["properties"]["template"]["containers"][0]["env"]
    return next(e["value"] for e in env if e["name"] == "ALLOWED_USERS")


def test_a_new_app_admits_nobody_until_sign_in_is_on(fake_az) -> None:  # type: ignore[no-untyped-def]
    """Review: the app was public with the real allowlist before Easy Auth was on, so a forged header got in."""
    fake = fake_az(exists=False)
    dz.app(["Owner@X.org"])
    assert allowed_in(fake.specs[0]) == ""
    assert fake.index("containerapp", "update") > fake.index("containerapp", "auth", "update")
    assert fake.allowed == "owner@x.org"


def test_a_failed_sign_in_step_leaves_a_new_app_admitting_nobody(fake_az) -> None:  # type: ignore[no-untyped-def]
    fake = fake_az(exists=False, fail=("containerapp", "auth", "update"))
    with pytest.raises(SystemExit):
        dz.app(["owner@x.org"])
    assert fake.allowed == "" and not [c for c in fake.calls if "--set-env-vars" in c]


def test_a_redeploy_keeps_and_reports_the_live_allowlist(fake_az, capsys) -> None:  # type: ignore[no-untyped-def]
    """Review: a redeploy printed the --allow list although the app kept the one grant_access.sh set."""
    fake = fake_az(exists=True, allowed="guest@y.org,owner@x.org")
    dz.app([])
    shown = capsys.readouterr().out
    assert "guest@y.org" in shown and "grant_access.sh" in shown
    assert not [c for c in fake.calls if "--set-env-vars" in c]


def test_a_new_app_needs_an_allow_email(fake_az) -> None:  # type: ignore[no-untyped-def]
    fake_az(exists=False)
    with pytest.raises(SystemExit, match="--allow"):
        dz.app([])


def test_an_api_redeploy_says_env_changes_are_not_applied(fake_az, monkeypatch, tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / ".env").write_text("AZURE_OPENAI_KEY=sk-new\n")
    monkeypatch.setattr(dz, "REPO_ROOT", tmp_path)
    fake_az(exists=True)
    dz.api()
    shown = capsys.readouterr().out
    assert "not re-applied" in shown and "sk-new" not in shown
