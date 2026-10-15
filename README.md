# Operations Portal

A shared internal-tools portal built to test whether Devin-assisted development can replace part of a roughly $250K-per-year Power Apps estate while keeping engineering effort and operational risk acceptable.

All companies, people, and figures are fictional.

## The question it answers

> “Can we use Devin to get the internal tools we need, reduce spending and gain flexibility — while keeping engineering effort and operational risk acceptable?”

The evaluation focuses on three measures:

- **Realized net platform savings:** spend that actually ends after transition and ongoing ownership costs.
- **Human effort per accepted change:** hands-on engineering time for useful, reviewed changes.
- **Reliable completion of operations:** whether workflows finish accurately, on time, and with the required controls.

These are evaluation measures, not results established by this prototype. The business-case calculator uses planning assumptions; savings require verified invoices, renewal dates, and costs that can stop.

## What's inside

| App | What it does | Power Apps tool it replaces |
| --- | --- | --- |
| Counterparty reviews | Reviews insurer, reinsurer, administrator, and MGA onboarding records with financial-strength and payout evidence. | KYC review queue |
| Claims & refunds | Records approval or rejection decisions for customer claims. Approval does not initiate payment. | Refunds dashboard |
| Feature flags | Reviews environment-level flags and records controlled changes. | Feature-flag admin |

### New apps

**Access reviews** records quarterly certification or revocation of employee access to business systems. It is a new workflow, not a replacement.

### Overview

- **Dashboard:** operational counts, enforced controls, and recent activity.
- **Business case:** editable spend, transition, ownership, and capacity assumptions.
- **Security & controls:** implemented controls, live counts, and production gaps.
- **Apps and delivery:** the app catalog, module guide, and measured build rounds.

### Records

- **Import & export:** validated CSV imports and audited dataset exports.
- **Audit log:** changes and data transfers within the signed-in role's audit scope.

## Security and controls

Protected API reads and writes check the signed-in role on the server. Record changes require a reason and expected version; the state change and its audit event are committed together and use the session identity. Imports are validated and all-or-nothing. Imports and exports are audited. Sessions expire after 8 hours by default; the in-process sign-in limiter allows five attempts per username and client IP per 15-minute window. Passwords use salted PBKDF2-HMAC-SHA256. The session cookie is HttpOnly and SameSite=Lax, and Secure for HTTPS requests. Blocked API actions and validation failures are counted on the dashboard.

This local prototype does not provide SSO or MFA, CSRF protection, DLP or equivalent egress controls, managed hosting, backups and tested recovery, encryption at rest for a managed database, immutable audit retention, production monitoring, or an independent security review. The login limiter is in memory and is not shared across workers. Production use needs managed identity, operational ownership, and an evidence-based security review.

## Run it locally

Requires Python 3.10 or newer.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open <http://localhost:8000>. The default database is `data/portal.db`; set `PORTAL_DB` to choose another path. Startup creates the schema and seeds data only when there are no users.

To clear and reseed the selected database:

```bash
PORTAL_DB=data/portal.db .venv/bin/python -m app.seed --reset
```

## Run with Docker

```bash
docker build -t ops-portal .
mkdir -p data
docker run --rm -p 8000:8000 -v "$PWD/data:/data" ops-portal
```

The container stores data at `/data/portal.db`. Mount a persistent directory. For shared or public use, set the deployment configuration below before the first seed.

## Accounts

The default password for all accounts is `demo`; `DEMO_PASSWORD` can override it before the database is first seeded.

| Username | Name | Role |
| --- | --- | --- |
| `rita.reviewer` | Rita Patel | Reviewer |
| `colin.claims` | Colin Murray | Claims operator |
| `fiona.flags` | Fiona Grant | Flag operator |
| `aaron.auditor` | Aaron Lee | Auditor |
| `nina.access` | Nina Okafor | Access reviewer |

All accounts can sign in and read the available pages. Mutations and protected API actions use server-side role checks.

## Configuration

| Variable | Default | Purpose | Shared/public deployment |
| --- | --- | --- | --- |
| `DEMO_PASSWORD` | `demo` | Password used when accounts are first seeded. | Set a unique, non-default value before first seed. |
| `SHOW_DEMO_ACCOUNTS` | `1` | Shows account names and the configured demo password on the sign-in page. | Set to `0`. |
| `SESSION_TTL_HOURS` | `8` | Session lifetime in hours. | Set to the approved session policy. |
| `PORTAL_COOKIE_SECURE` | Request scheme | `1` forces Secure; `0` disables it; unset follows HTTPS. | Set to `1` behind HTTPS. |
| `PORTAL_DB` | `data/portal.db` | SQLite database path; the container default is `/data/portal.db`. | Use a persistent, access-controlled location. |
| `PORT` | `8000` | Container listening port. | Set to the platform-assigned port if required. |

Changing `DEMO_PASSWORD` does not update existing password hashes; reset or recreate the database to seed accounts with a new value.

## Import and export

Download a template, validate a CSV, then commit only when every row is valid. Imports are limited to 1 MB and 1,000 rows. Counterparties, claims, and access reviews are importable; flags are not.

- `samples/counterparties_q4_onboarding.csv` contains three valid rows.
- `samples/claims_batch_with_errors.csv` contains five rows, including an unknown counterparty and an invalid amount.

Exports cover counterparties, claims, flags, access reviews, and audit data. Audit exports respect the signed-in user's audit scope. Successful imports and exports create audit events.

## Add an app

Follow the shared module guide in [Apps and delivery](/apps#add):

1. Add a versioned table and seed records. Define role permissions and audit scope; add a demo account only if the module needs a distinct role.
2. Create a router with permission-checked API reads and mutations through `run_command`. Register the router and `ModuleSpec`.
3. Add templates and forms. Test allowed actions, denied roles, reasons, stale versions, and import or export behavior.

The Access reviews app follows this pattern and reuses the existing sign-in, permissions, audit, and data-transfer foundations.

## Tests

```bash
.venv/bin/pytest -q
```

## Project layout

```text
app/
  core/       authentication, permissions, database, commands, audit, CSV rules
  modules/    counterparty, claims, flags, access reviews, data transfer, pages
  templates/  server-rendered pages
  static/     styles and browser scripts
  seed.py
  delivery_log.json
samples/      example import files
tests/        control, auth, and migration regressions
2. Planning/  decision log and planning records
3. Build/     build notes and evidence
```

## Build rounds and evidence

The initial prototype took 10.9 wall-clock minutes. The refinement round took 30.7 minutes; together they took about 42 minutes. Human time was not measured. See the [build notes](<3. Build/0.build-notes.md>) and [decision log](<2. Planning/1.decision-log.md>) for scope, choices, checks, and limitations.

## Limitations

This is a local prototype, not a production service. It uses SQLite and has no live identity, payment, insurer, or flag-provider integrations. Claim approval records a decision; the payments system remains responsible for payout. It has no shared rate limiter, enterprise sign-in, CSRF protection, data-loss prevention, managed recovery, tamper-evident audit retention, or production monitoring. Ownership, migration, incident response, and operator acceptance remain untested and should be addressed in a measured pilot.
