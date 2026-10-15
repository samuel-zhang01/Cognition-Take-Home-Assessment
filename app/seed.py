import argparse
import os

from app.core.auth import DEMO_USERS, hash_password, utc_now
from app.core.db import connect, init_db, transaction


def seed_if_empty(db_path):
    conn = connect(db_path)
    try:
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
            return False
        password = os.environ.get("DEMO_PASSWORD", "demo")
        now = utc_now()
        with transaction(conn):
            for username, display_name, role in DEMO_USERS:
                salt, digest = hash_password(password)
                conn.execute(
                    """INSERT INTO users
                       (username, display_name, role, password_salt, password_hash)
                       VALUES (?, ?, ?, ?, ?)""",
                    (username, display_name, role, salt, digest),
                )
            counterparties = [
                ("CP-001", "Northwind Mutual Assurance (fictional)", "insurer", "UK", "pending_review"),
                ("CP-002", "Harborlight Claims Services (fictional)", "claims_provider", "UK", "pending_review"),
                ("CP-003", "Juniper Shield Cooperative (fictional)", "insurer", "US", "pending_review"),
                ("CP-004", "Meridian Cover Group (fictional)", "insurer", "EU", "approved"),
            ]
            conn.executemany(
                """INSERT INTO counterparties
                   (id, name, kind, market, status, version, updated_at)
                   VALUES (?, ?, ?, ?, ?, 1, ?)""",
                [(*item, now) for item in counterparties],
            )
            evidence = [
                ("EV-001", "CP-001", "financial_strength_opinion", "Synthetic Rating Agency A", "rating_agency_opinion", "Northwind Mutual Assurance", "A- (synthetic)", "2025-01-15", "SYNTHETIC FIXTURE - not a real rating"),
                ("EV-002", "CP-001", "observed_payout_history", "Synthetic Internal Ledger", "internal_payout_records", "UK motor claims cohort", "212 claims paid, median 9 days (synthetic)", "2025-02-01", "SYNTHETIC FIXTURE - not real payout data"),
                ("EV-003", "CP-002", "financial_strength_opinion", "Synthetic Rating Agency B", "rating_agency_opinion", "Harborlight Claims Services", "BBB+ (synthetic)", "2025-01-20", "SYNTHETIC FIXTURE - not a real rating"),
                ("EV-004", "CP-002", "observed_payout_history", "Synthetic Internal Ledger", "internal_payout_records", "UK home claims cohort", "86 claims paid, median 12 days (synthetic)", "2025-02-04", "SYNTHETIC FIXTURE - not real payout data"),
                ("EV-005", "CP-003", "financial_strength_opinion", "Synthetic Rating Agency A", "rating_agency_opinion", "Juniper Shield Cooperative", "A (synthetic)", "2025-01-10", "SYNTHETIC FIXTURE - not a real rating"),
                ("EV-006", "CP-003", "observed_payout_history", "Synthetic Internal Ledger", "internal_payout_records", "US claims cohort", "145 claims paid, median 11 days (synthetic)", "2025-01-29", "SYNTHETIC FIXTURE - not real payout data"),
                ("EV-007", "CP-004", "financial_strength_opinion", "Synthetic Rating Agency C", "rating_agency_opinion", "Meridian Cover Group", "A (synthetic)", "2025-01-13", "SYNTHETIC FIXTURE - not a real rating"),
                ("EV-008", "CP-004", "observed_payout_history", "Synthetic Internal Ledger", "internal_payout_records", "EU claims cohort", "301 claims paid, median 8 days (synthetic)", "2025-02-02", "SYNTHETIC FIXTURE - not real payout data"),
            ]
            conn.executemany(
                """INSERT INTO counterparty_evidence
                   (id, counterparty_id, evidence_type, source, source_type,
                    rated_entity_or_market, value, as_of, provenance)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                evidence,
            )
            claims = [
                ("CLM-1001", "CP-001", "POL-88213", "Windshield repair", 24500, "GBP", "submitted"),
                ("CLM-1002", "CP-001", "POL-88214", "Water damage assessment", 128000, "GBP", "submitted"),
                ("CLM-1003", "CP-002", "POL-11903", "Travel delay expense", 32000, "GBP", "submitted"),
                ("CLM-1004", "CP-003", "POL-33071", "Laptop accidental damage", 79900, "USD", "submitted"),
                ("CLM-1005", "CP-003", "POL-33072", "Baggage replacement", 41800, "USD", "approved_simulated"),
                ("CLM-1006", "CP-004", "POL-55019", "Appliance repair", 9150, "EUR", "submitted"),
            ]
            conn.executemany(
                """INSERT INTO claims
                   (id, counterparty_id, claimant_ref, description, amount_minor,
                    currency, status, version, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)""",
                [(*item, now) for item in claims],
            )
            flags = [
                ("sandbox.new_claims_intake_form", "New claims intake form in the sandbox.", 0),
                ("sandbox.instant_status_updates", "Show immediate status updates in the demo.", 1),
                ("sandbox.partner_portal_v2", "Enable the fictional partner portal preview.", 0),
                ("sandbox.audit_export_preview", "Show a non-production audit export preview.", 1),
            ]
            conn.executemany(
                """INSERT INTO flags (key, description, enabled, version, updated_at)
                   VALUES (?, ?, ?, 1, ?)""",
                [(*item, now) for item in flags],
            )
            seed_entitlements(conn, now)
        return True
    finally:
        conn.close()


def reset_db(db_path):
    init_db(db_path)
    conn = connect(db_path)
    try:
        with transaction(conn):
            conn.execute("DELETE FROM audit_events")
            conn.execute("DELETE FROM sessions")
            conn.execute("DELETE FROM counterparty_evidence")
            conn.execute("DELETE FROM claims")
            conn.execute("DELETE FROM counterparties")
            conn.execute("DELETE FROM flags")
            conn.execute("DELETE FROM entitlements")
            conn.execute("DELETE FROM users")
        return seed_if_empty(db_path)
    finally:
        conn.close()


def seed_entitlements(conn, now=None):
    now = now or utc_now()
    entitlements = [
        ("ENT-001", "Maya Chen", "Finance", "Stripe Dashboard", "Refunds analyst", "2026-10-12T09:30:00+00:00", "certified", 4),
        ("ENT-002", "Oliver James", "Data", "Snowflake", "Analyst", "2026-10-14T15:10:00+00:00", "pending", None),
        ("ENT-003", "Priya Shah", "Platform", "AWS production console", "Read-only", "2026-10-15T08:40:00+00:00", "pending", None),
        ("ENT-004", "Daniel Foster", "Support", "Zendesk", "Team lead", "2026-10-11T11:25:00+00:00", "certified", 9),
        ("ENT-005", "Sofia Alvarez", "Engineering", "GitHub org admin", "Organization admin", "2026-10-13T17:05:00+00:00", "pending", None),
        ("ENT-006", "Ethan Brooks", "Security", "AWS production console", "Security auditor", "2026-10-15T06:55:00+00:00", "certified", 12),
        ("ENT-007", "Amara Okafor", "Finance", "Stripe Dashboard", "Finance operator", "2026-10-10T13:15:00+00:00", "pending", None),
        ("ENT-008", "Lucas Meyer", "Data", "Snowflake", "Data engineer", "2026-10-09T10:20:00+00:00", "revoked", 15),
        ("ENT-009", "Grace Liu", "Support", "Zendesk", "Support agent", "2026-10-14T12:45:00+00:00", "certified", 20),
        ("ENT-010", "Noah Williams", "Platform", "AWS production console", "Deploy operator", "2026-10-08T18:10:00+00:00", "pending", None),
        ("ENT-011", "Isabella Rossi", "Engineering", "GitHub org admin", "Repository maintainer", "2026-10-12T14:20:00+00:00", "certified", 24),
        ("ENT-012", "Ava Thompson", "Finance", "NetSuite", "Accounts payable", "2026-10-07T16:35:00+00:00", "pending", None),
        ("ENT-013", "Leo Martin", "Data", "Snowflake", "Read-only analyst", "2026-10-06T09:05:00+00:00", "revoked", 28),
        ("ENT-014", "Zara Ahmed", "Security", "Okta Admin", "Helpdesk administrator", "2026-10-13T07:50:00+00:00", "pending", None),
        ("ENT-015", "Theo Wilson", "Support", "Zendesk", "Support manager", "2026-10-15T10:00:00+00:00", "certified", 30),
    ]
    from datetime import datetime, timedelta, timezone

    base = datetime.now(timezone.utc)
    for row in entitlements:
        entitlement_id, employee, team, system, access_level, last_used, status, offset = row
        decided_at = (base - timedelta(days=offset)).isoformat() if offset else None
        conn.execute(
            """INSERT INTO entitlements
               (id, employee, team, system, access_level, last_used_at, quarter,
                status, decided_at, version, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, '2026-Q4', ?, ?, 1, ?)""",
            (
                entitlement_id,
                employee,
                team,
                system,
                access_level,
                last_used,
                status,
                decided_at,
                decided_at or last_used or now,
            ),
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    db_path = os.environ.get("PORTAL_DB", "data/portal.db")
    if args.reset:
        reset_db(db_path)
    else:
        init_db(db_path)
        seed_if_empty(db_path)


if __name__ == "__main__":
    main()
