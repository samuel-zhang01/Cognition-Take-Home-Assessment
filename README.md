# Shared operations portal

This prototype helps evaluate whether a small engineering team could build focused internal tools with Devin, reduce platform spend, and retain acceptable control over delivery and operations. It pairs thin workflows with one authentication, permissions, SQLite, and audit foundation.

All companies, people, and figures are fictional.

## What is included

| Tool | Workflow |
| --- | --- |
| Counterparty reviews | Review insurer, reinsurer, claims administrator, and MGA onboarding records with separate financial-strength and payout-history evidence. |
| Claims & refunds | Record an approval or rejection for a customer claim. Approval does not initiate a payment. |
| Feature flags | Change a flag with an owner, environment, reason, version check, and audit entry. |
| Access reviews | Certify or revoke employee access for the 2026-Q4 review period. |

The dashboard summarizes each workflow, recent in-scope activity, import and export counts, and control outcomes. The business case page lets a reviewer vary avoidable spend, transition cost, recurring ownership, and capacity assumptions. The app catalog reports source lines and the round in which each app was built. The delivery log records two rounds of wall-clock effort and human time, which was not measured.

## Build rounds

The initial prototype ran from 2026-10-15T17:17:23Z to 2026-10-15T17:28:16Z, about 11 minutes. The refinement round ran from 2026-10-15T17:47:07Z to 2026-10-15T18:17:48Z, about 31 minutes; together the rounds took 42 wall-clock minutes. The 0.9-minute Access Reviews measurement, 17:48:17Z to 17:49:11Z, only covered applying an already written module spec; it is not used as build time. The change was 10 files changed, 205 insertions(+), 5 deletions(-).

Rounds were timed from brief to last commit. Commits were batched, so per-commit timing is not meaningful. Human time was not measured.

## Run it

Requires Python 3.10 or newer.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000`. Data is stored in `data/portal.db` by default. Set `PORTAL_DB` to select another path. The application creates the schema and seeds records only when the users table is empty; restarting preserves state and history.

To explicitly clear and reseed the database:

```bash
PORTAL_DB=data/portal.db .venv/bin/python -m app.seed --reset
```

After changing the schema, delete the existing database before starting the application so the new schema is created.

Run the tests and build the container with:

```bash
.venv/bin/pytest -q
docker build -t ops-portal .
```

## Accounts

The password for all accounts is `demo` unless `DEMO_PASSWORD` is set before the database is first seeded.

| Username | Display name | Role | Write access | Audit scope |
| --- | --- | --- | --- | --- |
| `rita.reviewer` | Rita Patel | reviewer | Counterparty decisions and counterparty imports | Counterparties |
| `colin.claims` | Colin Murray | claims operator | Claim decisions and claim imports | Claims |
| `fiona.flags` | Fiona Grant | flag operator | Feature-flag changes | Flags |
| `aaron.auditor` | Aaron Lee | auditor | Read-only | All modules |
| `nina.access` | Nina Okafor | access reviewer | Access decisions and entitlement imports | Access reviews |

All accounts can read the application modules. Every API mutation checks its permission on the server. Session identity comes from the database session record, not from request fields. The shared `run_command` helper validates the reason, checks the expected version, applies the state transition, and writes the audit event in one transaction. Failed commands roll back their mutation and audit write; a separate control event records the denied or stale attempt.

## Import and export

Open **Import & export** to download a CSV template, validate a file, and then commit a valid batch. Imports are limited to 1 MB and 1,000 rows. A batch with any error is not written. Each successful dataset import creates one audit event with its filename, row count, and reason.

Counterparties, claims, and access entitlements can be imported. Feature flags are not importable. The supplied batches are:

- `samples/counterparties_q4_onboarding.csv`: three valid counterparty records.
- `samples/claims_batch_with_errors.csv`: five claims, including an unknown counterparty and an invalid amount for validation.

Counterparties, claims, flags, access reviews, and audit events can be exported. Audit CSV and JSON exports contain only events within the current account's audit scope. Exports are recorded in the shared audit log.

## Add a module

Use the shared module pattern rather than creating a separate application foundation:

1. Add a versioned table and seed records in `app/core/db.py` and `app/seed.py`. Add the module's permissions and `AUDIT_SCOPE` entry in `app/core/permissions.py`. When the module needs a distinct role, add a session-backed demo account to `DEMO_USERS` in `app/core/auth.py`.
2. Create `app/modules/<name>.py`. Protect reads with `require_permission`; route each mutation through `run_command` with a reason, expected version, and transition function. Register the router in `app/main.py` and the `ModuleSpec` in `app/core/registry.py`.
3. Add templates using `base.html`, `command-form`, `app.js`, and `audit_rows.html`. Add tests for allowed actions, denied roles, invalid reasons, stale versions, and any import or export behavior.

The Access reviews module was added by following these steps. Its focused implementation touched the shared schema, permissions, demo identity, router, registry, page, seed records, and tests.

## Limitations

This is a local prototype, not a production service. For any shared or public deployment, set `SHOW_DEMO_ACCOUNTS=0` and a non-default `DEMO_PASSWORD` before the first seed. It has no enterprise SSO, MFA, CSRF protection, managed hosting, backups, monitoring, or tamper-evident audit retention. It has no live insurer, payment, flag-provider, or identity integrations. Claim approval records an operational decision; the payments system remains responsible for payout. Production use requires security review, data migration and retention decisions, ownership planning, incident response, and evidence from a measured pilot.
