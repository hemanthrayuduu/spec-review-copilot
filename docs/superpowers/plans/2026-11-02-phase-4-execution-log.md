# Phase 4 execution log: test, Docker, hosting, README, polish

- **Phase 4a** (the labeling helper) merged at d09a0eb.
- **Phase 4b** ran on main through short branches, each merged after a green suite: commits 6673fef..fc35c5f.
  The plan was approved in plan mode on 2026-11-01. Its steps are the headings below.
- **Tests:** 690 pass with no network and no keys (`uv run pytest`). ruff is at main's baseline of 2 errors,
  and no new mypy errors were added.

## Phase 4 report against spec section 10

| Criterion | Result | Evidence |
|---|---|---|
| The test scorecard is saved and reported as is, and the README says the test package is synthetic | Met | `docs/scorecards/test-cedar-falls.json` and `docs/scorecards/README.md`, unchanged since the run. README, "Read these numbers with care" |
| Docker compose runs the API and the app locally | Met | `docker compose up --build`: the Lakeview sample ran in 33 s with 398 of 398 replies cached, $0 |
| The demo is hosted on Azure Container Apps | Met | Below, "Hosting". The owner signed in on 2026-11-02 and the app let them in |
| The README is complete, with honest results and limitations | Met | `README.md`: the problem, architecture, results with both failed gates, local and hosted runs, limitations, what production needs |

## What each step did

- **0. Merge 4a.** Fast-forward to d09a0eb.
- **1. Freeze (6673fef, tag `phase4-freeze`).** `docs/FREEZE.md` holds the scored config and a SHA-256 over the
  pipeline code and the knowledge files. `tests/test_freeze.py` fails if anything drifts, and `eval test`
  refuses to run on a drifted config.
- **2. Rule amendments (b8ef549).** These follow the owner's decision of 2026-11-01: the test set is one
  synthetic package, written after the freeze, with labels only from its generator. The change went into
  CLAUDE.md rules 5–6, the spec (sections 3, 9, 10), PHASE_PROMPTS, `/eval` and the hands-on guide.
- **3. Cedar Falls (fd042af).** The package is 120 pages with 3 addenda, a scoring table and data forms,
  140 requirements, and 7 traps. The generator tests check only the generator. The pipeline never ran on the
  package before step 4.
- **4. One test run (c0ffa11, 5457ed4).** `eval test` runs once. It refuses when the scorecard exists or the
  config drifted. The run was saved as it came out:
  - recall 0.950;
  - mandatory recall 0.948, just under the 95% target;
  - precision 0.162;
  - two gates failed: candidate recall 0.993 and red flags 0.857;
  - cost $1.14.

  Five fixes are listed and not applied.
- **5. Docker (cacf25c, eea0ea0, b05cc90).**
  - One image serves both the API and the app. It runs as a non-root user, has Tesseract installed, and uses
    `uv sync --locked`.
  - Compose runs the API and the app with a health check.
  - `scripts/demo.sh` runs Lakeview in mock mode with no keys.
- **6. Access (691292c).** `app/access.py` admits only `ALLOWED_USERS`, read from the header the platform's
  sign-in sets. Hosted mode hides the labeling helper and the API box and records decisions under the
  signed-in email. `scripts/grant_access.sh` grants and removes access.
- **7. Hosting (939b15e..c696838).** `scripts/deploy_azure.py` has four steps: base, image, api, app. See
  "Hosting" below.
- **8. README (d1660ca).**
- **9. Polish (b64b6a7, fc35c5f).** Five rough edges from Phase 3 were fixed, each test first, then checked in a
  real browser:
  - The Outputs page fetches a file only on click. The API log showed 0 file requests after Generate and 1
    after one click.
  - A finished run shows in the run picker without a reload, and there is no redraw loop: `GET /runs` stayed
    flat for 8 s.
  - Reviewer survives a reload and a page change, through `?reviewer=`.
  - There is no Deploy button.
  - The booster pump's two items read "flow 40 gpm" and "pressure 80 psi".

## Hosting

**Resources** (resource group `rg-specreview-demo-gwc`, Germany West Central, Azure for Students):

| Resource | What it is |
|---|---|
| `acrspecreviewdemo` | Private registry, Basic, no admin user. Apps pull with the managed identity `id-specreview-pull` (AcrPull). |
| `stspecreviewdemo` / share `specreview` | `runs/` (runs, `reviews.sqlite`, `latest`) and `uploads/`, mounted at uid 1000 with `mfsymlinks,nobrl` |
| `cae-specreview-demo-gwc` | Container Apps environment, workload-profiles mode with only the Consumption profile, no log workspace |
| `ca-specreview-api` | Internal ingress only. 1 vCPU and 2 GiB, 0 to 1 replicas. Three keys as secrets |
| `ca-specreview-app` | Public, with sign-in required for every request (Microsoft, any account). 0.5 vCPU and 1 GiB, 0 to 1 replicas |
| Entra app "Spec Review Copilot (demo)" | Any Microsoft account, v2 tokens. Its client secret expires after 1 year |

**Checked on 2026-11-02:**
- **Sign-in:** an anonymous browser visit is redirected to Microsoft sign-in, and a non-browser request gets
  401. The owner signed in with the allowed email and the app let them in.
- **API isolation:** the API answers 404 from the internet, under its internal name and its plain name.
- **Lakeview sample:** run from inside the environment, it went through 13 of 13 stages in 51 s. 398 of 398
  replies came from the cache, so it cost $0, and it found 319 items, the same as locally.
- **Outputs:** all five were generated.
- **Persistence:** after an API restart on a new replica, the run and its outputs were still there, and the
  xlsx and PDF downloaded intact.
- **Not yet seen live:** an account that isn't allowed being refused, and a decision surviving a restart in
  the UI. Both are covered by tests (`tests/test_access.py`, `tests/test_app.py`), and the hands-on guide
  section 12 walks through them.

**Spend:**

| Item | Cost |
|---|---|
| The test run | $1.14 |
| The registry | About $0.17 a day |
| Container Apps | Within the free monthly grant so far |
| Storage | Cents |
| Hosted Azure OpenAI | $0, since the replies were cached |

## Bugs found while hosting, fixed test first

1. **Express environment (b4edfd4).** The preview CLI makes an Express environment by default, and Express
   can't mount storage. The environment is now created in workload-profiles mode.
   - Test: `test_environment_is_not_express_because_express_cannot_mount_the_share`.
2. **Sign-in registration (d2588fd).** Graph refused `api.requestedAccessTokenVersion` as a dotted path. One
   PATCH now sets the audience, v2 tokens and redirect, and it runs on every deploy.
   - Test: `test_sign_in_registration_takes_any_microsoft_account_even_when_it_already_exists`.
3. **Missing image (c696838).** A commit after the image step left the app pointing at an image that didn't
   exist. Deploy now takes `--tag` and refuses a tag the registry doesn't have.
   - Tests: `test_a_named_tag_is_used_as_is_without_asking_git`,
     `test_apps_are_not_pointed_at_an_image_the_registry_does_not_have`.

## Rulings

- **Azure Files, not Blob storage.** Spec section 3 names Blob. The API reads and writes runs, SQLite and
  uploads as files, and a file share mounts as a folder with no code change. Cost if wrong: a storage layer
  later, if packages move to Blob.
- **Sign-in accepts any Microsoft account, and the email allowlist decides who gets in.** The owner wants to
  invite people outside Northeastern. The README names the caveat: production should key access on tenant
  and object IDs. Cost if wrong: someone who can sign in under an allowed address would get in. The data is
  synthetic or public; the real exposure is Azure OpenAI spend on uploads.
- **The image is built locally with `docker buildx`, not ACR Tasks.** That build was already tested with
  compose. Cost if wrong: none.
- **The image tag is the commit.** Deploy refuses uncommitted changes to tracked files. Cost if wrong: a
  rebuild per commit, about 3 minutes.
- **On a redeploy, the apps get only a new image.** The allowlist, secrets and sign-in stay as they are.
  Settings change through `grant_access.sh` or `az containerapp update`. Cost if wrong: a settings change
  needs a manual step.
- **`review_exceptions.csv` stays in the API container when hosted,** and is lost on a restart. Decisions are
  in SQLite on the share, and the outputs come from them. Cost if wrong: the hosted deviation log restarts
  empty.
- **Reviewer lives in the address bar** (`?reviewer=`), not in a cookie, because Streamlit can read cookies
  but not set them. Hosted mode ignores it and uses the signed-in email. Cost if wrong: none.

## Final review

A fresh reviewer on Opus read the code changes d09a0eb..fc35c5f, leaving out the held-out test content.
- **Found:** no Critical findings, 3 Important, and 6 Minor.
- **Raised:** I raised two of the Minors to Important because of what they would do to a user.
- **Fixed:** all five in one pass, each with a test that failed first. The suite went from 681 to 690.

1. **A new hosted app was public before sign-in was on.** Two auth calls follow the create. In that window,
   or for good if a call failed, a forged `X-MS-CLIENT-PRINCIPAL-NAME` header would have been let in as an
   allowed email. A new app now starts with an empty allowlist, and the emails go in only after both calls
   succeed. Today's deployment was already past this window.
   - Tests: `test_a_new_app_admits_nobody_until_sign_in_is_on`,
     `test_a_failed_sign_in_step_leaves_a_new_app_admitting_nobody`.
2. **Compose published both ports on every network.** Anyone on the same Wi-Fi could have used the API and
   spent the `.env` keys. Both ports are now bound to 127.0.0.1.
   - Test: `test_compose_publishes_its_ports_on_this_machine_only`.
3. **A redeploy printed settings it didn't apply.** It showed the `--allow` list, which a rerun doesn't apply,
   and it didn't say that `.env` keys aren't re-applied. It now prints the live allowlist and says what a
   rerun leaves alone. `--allow` is needed only for a new app.
   - Tests: `test_a_redeploy_keeps_and_reports_the_live_allowlist`, `test_a_new_app_needs_an_allow_email`,
     `test_an_api_redeploy_says_env_changes_are_not_applied`.
4. **Raised to Important: only the root `.env` was excluded from the image.** A stray copy would have shipped
   to the registry, and a `runs/.env` does exist on this Mac (`runs/` is excluded anyway). Now `**/.env*`
   and `**/.streamlit/secrets.toml` are excluded.
   - Test: `test_dockerignore_keeps_every_env_copy_and_streamlit_secrets_out`.
5. **Raised to Important: the hosted API could scale to zero during a job.** Polling ran only on the Run
   page. A sidebar check now runs every 10 s on every page while a job runs, and redraws the app once when
   it finishes.
   - In a real browser on the Brief page, the caption read "stage 12 of 13", the run picker switched to the
     new run, and polling stopped afterwards.
   - Tests: `test_a_running_job_keeps_the_api_awake_from_any_page`,
     `test_a_finished_job_is_no_longer_checked_from_the_sidebar`.

**Deferred minors:**
- The eval-test guard is only the scorecard file. A crash mid-run, or an old checkout, would allow a second
  run. That is moot now that the scorecard exists.
- `grant_access.sh remove` treats the email as a regex (`grep -vx`). It should be `grep -Fvx --`.
- A failed download shows only Streamlit's generic message, not the API's reason.
- The storage key is passed to `az` on the command line. It is visible in `ps` on this Mac while the command
  runs.

**Rulings on what the reviewer declined to judge:**
- **Header spoofing once sign-in is on.** The Container Apps docs say: "External requests aren't allowed to
  set these headers, so they're present only if set by Container Apps." The app relies on that. Cost if
  wrong: a signed-in visitor could pose as an allowed email.
- **Which claim fills the principal name.** This is covered by the email-allowlist ruling above.
- **SQLite on the share during a revision swap.** Two replicas can overlap for a moment while a new image
  rolls out, and only decisions write to the database. Accepted for the demo. Cost if wrong: a decision made
  during a rollout could be lost.
- **Whether `az containerapp update --set-env-vars` keeps the secrets.** Secrets are stored apart from
  environment variables, and the deploy fix itself uses this call. It will be checked live on the next
  grant.
