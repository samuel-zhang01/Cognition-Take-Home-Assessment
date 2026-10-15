# Cognition take-home: shared internal tools

A small **shared operations portal** prototype built with Devin Cloud, plus the research and planning behind a build-versus-buy recommendation for a Series C fintech currently paying ~$250K/year for Microsoft Power Apps (KYC review queue, refunds dashboard, feature-flag admin, 10+ more tools planned).

The prototype is a **proof of concept, not a production system**. It uses insurance-informed examples (Samuel's background) as an explicit proxy for the fintech's tools; real fintech requirements still need discovery.

| Assessment tool | Insurance proxy in this demo | Working slice |
| --- | --- | --- |
| KYC review queue | Fictional insurer / claims-provider counterparty review | Inspect synthetic evidence; approve or reject with a required reason. |
| Refunds dashboard | Claim / payment request | Inspect linked counterparty; record a **simulated** approval with a reason. No money moves; approval is not settlement. |
| Feature-flag admin | Sandbox configuration flags | Toggle one boolean with a reason. |
| (shared) | Cross-tool audit | One role-scoped history view, filterable by module and resource. |

Counterparty review is **not** a complete KYC identity/compliance engine, and a claim is not identical to a fintech refund. All entities, ratings and payout figures are fictional and labelled synthetic. Counterparty approval does **not** automatically authorize claims — the counterparty status is shown on a claim as context only.

## Run it

Requires Python 3.10+.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --port 8000
# open http://localhost:8000
```

- Data lives in SQLite at `data/portal.db` (override with `PORTAL_DB=/path/to.db`). It is created and seeded on first start only; restarts keep state and history.
- **Reset to fixtures (explicit, destructive):** `.venv/bin/python -m app.seed --reset` (deletes all rows, reseeds). After a schema change, delete `data/portal.db` instead.
- **Tests:** `.venv/bin/pytest -q`
- **Container:** `docker build -t ops-portal . && docker run -p 8000:8000 -v portal-data:/data ops-portal`

### Demo accounts (demo authentication, not enterprise SSO)

Password for all accounts: `demo` (override with `DEMO_PASSWORD` before first start).

| Username | Role | Can mutate | Audit history visible |
| --- | --- | --- | --- |
| `rita.reviewer` | reviewer | Record counterparty review | Counterparties |
| `colin.claims` | claims_operator | Simulate claim approval | Claims |
| `fiona.flags` | flag_operator | Change sandbox flag | Flags |
| `aaron.auditor` | auditor | Nothing (read-only) | All modules |

All roles can read the synthetic module records. The permission map lives in one file: [`app/core/permissions.py`](app/core/permissions.py). Hiding a button is UX only; every endpoint checks permissions on the server, and identity always comes from the server-side session, never from the request body.

## How it is built

FastAPI + stdlib SQLite + server-rendered Jinja templates; a few lines of JavaScript ([`app/static/app.js`](app/static/app.js)) post forms to the same JSON API used by the direct API checks. See decision log D023–D025 for why (no React/Node).

```
app/core/        shared foundation used by every module
  auth.py          demo users, server-side sessions (HttpOnly cookie), current_user / require_permission
  permissions.py   ROLE_PERMISSIONS and AUDIT_SCOPE (single source of truth)
  commands.py      run_command(): the one mutation path
  audit.py         write_audit / list_audit (role-scoped reads)
  db.py            schema, BEGIN IMMEDIATE transaction helper
  registry.py      MODULES: what appears on the home page and nav
app/modules/     counterparties.py, claims.py, flags.py, audit_view.py
app/seed.py      synthetic fixtures; --reset
tests/test_controls.py  behaviour checks below
```

`run_command` does, in order: permission check → reason validation (3–500 chars) → `BEGIN IMMEDIATE` → load row → expected-version check → module transition function → `UPDATE … WHERE version = ?` → audit insert → commit. State change and audit event commit together or not at all. Unknown request fields (e.g. a forged `actor` or `role`) are ignored.

## Add a module (engineer path)

1. Add the table to `SCHEMA` in `app/core/db.py` with a `version INTEGER NOT NULL DEFAULT 1` and `updated_at` column; add fixtures to `app/seed.py`.
2. Add permissions (e.g. `vendor.read`, `vendor.update`) to the right roles in `app/core/permissions.py`, and the module key to `AUDIT_SCOPE` for whoever may read its history.
3. Create `app/modules/<name>.py` with an `APIRouter`. Reads use `Depends(require_permission("<name>.read"))`. Each mutation defines a pydantic body (`extra="ignore"`, `reason`, `expected_version`), a small `apply(row) -> changes` function that raises `InvalidTransition` for illegal moves, and calls `run_command(...)`. Copy `flags.py` — it is the smallest example.
4. Register it: `include_router` in `app/main.py`, and a `ModuleSpec` in `app/core/registry.py` (home card + nav).
5. Add templates using `base.html`, `command-form` forms (handled by `app.js`) and `audit_rows.html`.
6. Add tests to `tests/test_controls.py` for: happy path + audit row, denied role, missing reason, stale version.

For a module-specific role, add the role to `ROLE_PERMISSIONS` and `AUDIT_SCOPE`, and add its demo account to `DEMO_USERS` in `app/core/auth.py`. Seed the account and module records through the shared seed function.

In practice an engineer gives Devin a prompt such as *"Add a vendor-contract module following the add-a-module steps in the README; owner role vendor_manager; one action: mark contract renewed with a reason"*, then reviews the PR.

### Non-engineer change request path (illustrative)

A claims operations lead asks Devin (e.g. via Slack): *"Claims should show the claimant reference on the list page."* Devin opens a branch and PR with the change and runs `pytest`; an engineer who owns the portal reviews the diff and merges. Repository authority (who can merge) is separate from operational authority (who can approve claims). **This path is described, not exercised in this build;** no independent human review of this code has happened yet.

## Verification (actual results)

`.venv/bin/pytest -q` → see [build notes](<3. Build/0.build-notes.md>) for recorded output. The checks map to the plan:

| Check | Test |
| --- | --- |
| Each role's action works and appears in the auditor's shared history with the right actor/module | `test_each_role_can_make_its_happy_path_change_and_auditor_sees_it` |
| Auditor mutations → 403 on all three endpoints; reviewer → claim approval 403; claims op → flag change 403; no state/audit change | `test_forbidden_mutations_do_not_change_state_or_audit` |
| Forged `actor`/`role` in the body does not change attribution or grant authority; no session → 401 | `test_forged_identity_is_ignored_and_missing_session_is_unauthorized` |
| Missing reason → 422; invalid transitions → 409; stale version → 409; no audit rows or version bumps | `test_reasons_transitions_and_stale_versions_never_write_extra_audits` |
| Two writes from one starting version (sequential and two concurrent threads) → exactly one 200 and one audit event | `test_same_starting_version_writes_only_once` |
| Restart preserves state/history; reset is explicit | `test_restart_preserves_state_and_reset_reseeds` |
| Counterparty ↔ claim links reference the same record; reviewer audit scope excludes other modules | `test_claim_counterparty_linkage_and_audit_scope` |

## Known limitations (not demonstrated)

- Demo passwords and SQLite sessions — no SSO/MFA, session expiry, CSRF tokens (SameSite=Lax + JSON only), rate limiting or account lifecycle.
- The audit table is an ordinary, mutable SQLite table — not tamper-evident or retained evidence.
- SQLite single-writer locking is fine for a demo; not a production concurrency/availability design. No backups, monitoring or incident process.
- No real rating feeds, payment providers, connectors or MCP. Fixtures only.
- No maker/low-code experience for non-engineers; changes go through Devin + code review.
- Tests are synthetic behaviour checks, not a security review.

## Research, planning and evaluation

- [Research and economics](<1. Research/0.research.md>) · [Insurance proxy and Code Apps comparison](<1. Research/evidence/insurance-proxy-and-code-apps.md>)
- [Prototype plan](<2. Planning/0.prototype-plan.md>) · [Decision log](<2. Planning/1.decision-log.md>) · [Original Devin handoff prompt](<2. Planning/2.devin-handoff-prompt.md>)
- [Build notes: time, effort, checks, gaps](<3. Build/0.build-notes.md>)
- [Assessment brief](./_instructions.md)
