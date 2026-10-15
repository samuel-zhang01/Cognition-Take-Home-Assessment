import argparse
import json
import os
from datetime import datetime, timedelta, timezone

from app.core.auth import DEMO_USERS, hash_password
from app.core.db import connect, init_db, transaction


COUNTERPARTIES = (
    ("Harbourline Mutual", "insurer", "United Kingdom", "UK-FCA-284193", "low", "pending_review", 3, 0, ""),
    ("Northgate Specialty Re", "reinsurer", "Ireland", "IE-CBI-771204", "medium", "pending_review", 6, 0, ""),
    ("Calder & Finch Claims Services", "claims administrator", "United Kingdom", "UK-FCA-639118", "medium", "pending_review", 9, 0, ""),
    ("Alderbrook General Insurance", "insurer", "United States", "US-NAIC-90842", "low", "pending_review", 12, 0, ""),
    ("Westmere Risk Partners", "MGA", "Netherlands", "NL-AFM-418276", "high", "pending_review", 14, 0, ""),
    ("Redwood Indemnity Group", "insurer", "United States", "US-NAIC-73015", "low", "approved", 18, 3, "Financial strength and claims controls meet the current review criteria."),
    ("Larkspur Reinsurance", "reinsurer", "Switzerland", "CH-FINMA-150982", "medium", "approved", 21, 5, "Capital position and settlement reporting were reviewed."),
    ("Stonebridge Claims Network", "claims administrator", "United Kingdom", "UK-FCA-295674", "low", "approved", 16, 2, "Service levels and escalation ownership were confirmed."),
    ("Elmstead Underwriting", "MGA", "Australia", "AU-ASIC-602918", "medium", "approved", 24, 4, "Delegated authority and bordereau controls were reviewed."),
    ("Cedar Vale Assurance", "insurer", "Germany", "DE-BAFIN-882041", "low", "approved", 27, 6, "Financial assessment and payout history support approval."),
    ("Bluehaven Claims Bureau", "claims administrator", "Canada", "CA-OSFI-503196", "high", "rejected", 11, 2, "Ownership evidence was incomplete at the review deadline."),
    ("Mariner's Point Underwriting", "MGA", "United Kingdom", "UK-FCA-741083", "high", "rejected", 19, 3, "The delegated authority schedule did not match the submitted register."),
)

RATINGS = (
    ("A-, stable outlook", "Kestrel Ratings"),
    ("BBB+, stable outlook", "Northstar Credit Review"),
    ("A, positive outlook", "Kestrel Ratings"),
    ("A-, stable outlook", "Arbor Financial Assessment"),
    ("BBB, watch positive", "Northstar Credit Review"),
    ("A+, stable outlook", "Kestrel Ratings"),
    ("A-, stable outlook", "Arbor Financial Assessment"),
    ("BBB+, stable outlook", "Northstar Credit Review"),
    ("A, stable outlook", "Kestrel Ratings"),
    ("A-, positive outlook", "Arbor Financial Assessment"),
    ("BBB-, negative outlook", "Northstar Credit Review"),
    ("BB+, stable outlook", "Arbor Financial Assessment"),
)

PAYOUTS = (
    "Median payout 11 days, trailing 12 months",
    "Median payout 14 days, trailing 12 months",
    "Median payout 8 days, trailing 12 months",
    "Median payout 10 days, trailing 12 months",
    "Median payout 16 days, trailing 12 months",
    "Median payout 9 days, trailing 12 months",
    "Median payout 13 days, trailing 12 months",
    "Median payout 7 days, trailing 12 months",
    "Median payout 12 days, trailing 12 months",
    "Median payout 10 days, trailing 12 months",
    "Median payout 22 days, trailing 12 months",
    "Median payout 19 days, trailing 12 months",
)

CLAIM_TYPES = (
    "travel disruption",
    "device damage",
    "card fraud refund",
    "duplicate charge refund",
    "merchant dispute",
)

CLAIM_DESCRIPTIONS = (
    "Overnight accommodation after a cancelled connection",
    "Screen replacement following accidental damage",
    "Card purchase reported as unauthorised",
    "Second charge posted for the same order",
    "Cardholder disputes a merchant's service charge",
    "Meals and local transport after a long delay",
    "Laptop repair following an accidental drop",
    "Refund request for a card-not-present transaction",
    "Duplicate subscription renewal charge",
    "Goods not received after merchant confirmation",
)

FLAGS = (
    ("payments.instant_refunds", "Allow eligible card refunds to settle immediately.", 1, "production", "Payments", 2, "Refund thresholds and monitoring were confirmed."),
    ("kyc.enhanced_due_diligence", "Request enhanced checks for higher-risk applications.", 1, "production", "Financial Crime", 5, "The review threshold was aligned with the current policy."),
    ("onboarding.open_banking_uk", "Offer open-banking verification to UK applicants.", 1, "production", "Onboarding", 3, "Provider coverage was confirmed for the UK journey."),
    ("claims.fast_track_travel", "Fast-track low-value travel disruption claims.", 0, "staging", "Claims Operations", None, None),
    ("cards.chargeback_evidence_v2", "Show the revised evidence checklist to dispute handlers.", 1, "production", "Cards", 8, "The checklist is ready for the next handler cohort."),
    ("risk.device_claims_triage", "Route repeat device claims to specialist review.", 0, "staging", "Risk", 1, "The triage rule was paused for calibration."),
    ("support.refund_status_banner", "Show refund status and expected timing in support tools.", 1, "production", "Customer Support", 6, "Support content and status definitions were reviewed."),
    ("settlement.merchant_reconciliation_v3", "Use the updated merchant reconciliation workflow.", 0, "staging", "Settlement", None, None),
)

ENTITLEMENTS = (
    ("Maya Chen", "Finance", "Stripe Dashboard", "Refunds analyst", 2, "certified", 5, "Access retained for daily refund reconciliation."),
    ("Oliver James", "Data", "Snowflake", "Analyst", 1, "pending", None, None),
    ("Priya Shah", "Platform", "AWS production console", "Read-only", 1, "pending", None, None),
    ("Daniel Foster", "Support", "Zendesk", "Team lead", 3, "certified", 11, "Team lead duties still require queue configuration access."),
    ("Sofia Alvarez", "Engineering", "GitHub org admin", "Organization admin", 4, "pending", None, None),
    ("Ethan Brooks", "Security", "AWS production console", "Security auditor", 1, "certified", 14, "Security evidence review remains part of the quarterly control."),
    ("Amara Okafor", "Finance", "Stripe Dashboard", "Finance operator", 2, "pending", None, None),
    ("Lucas Meyer", "Data", "Snowflake", "Data engineer", 5, "revoked", 18, "Project access ended after the data migration."),
    ("Grace Liu", "Support", "Zendesk", "Support agent", 1, "certified", 20, "Queue access is required for the current support rota."),
    ("Noah Williams", "Platform", "AWS production console", "Deploy operator", 3, "pending", None, None),
    ("Isabella Rossi", "Engineering", "GitHub org admin", "Repository maintainer", 2, "certified", 24, "Maintainer access is limited to the service repositories."),
    ("Ava Thompson", "Finance", "NetSuite", "Accounts payable", 4, "pending", None, None),
    ("Leo Martin", "Data", "Snowflake", "Read-only analyst", 6, "revoked", 29, "Reporting assignment ended."),
    ("Zara Ahmed", "Security", "Okta Admin", "Helpdesk administrator", 1, "pending", None, None),
    ("Theo Wilson", "Support", "Zendesk", "Support manager", 1, "certified", 30, "Manager access is needed for escalation coverage."),
)


def _at(base, days=0, hours=0):
    return (base - timedelta(days=days, hours=hours)).isoformat(timespec="seconds")


def _seed_audit(
    conn,
    *,
    at,
    actor_username,
    actor_role,
    module,
    resource_type,
    resource_id,
    action,
    reason,
    before,
    after,
):
    conn.execute(
        """INSERT INTO audit_events
           (at, actor_username, actor_role, module, resource_type, resource_id,
            action, reason, before_json, after_json, resource_version, details)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, NULL)""",
        (
            at,
            actor_username,
            actor_role,
            module,
            resource_type,
            resource_id,
            action,
            reason,
            json.dumps(before, sort_keys=True),
            json.dumps(after, sort_keys=True),
        ),
    )


def _seed_counterparties(conn, base):
    for index, item in enumerate(COUNTERPARTIES, start=1):
        name, kind, country, registration, risk, status, submitted_days, decision_lag, reason = item
        submitted_at = _at(base, submitted_days)
        decided_at = _at(base, submitted_days - decision_lag) if status != "pending_review" else None
        counterparty_id = f"CP-{index:03d}"
        conn.execute(
            """INSERT INTO counterparties
               (id, name, kind, country, registration_number, risk_tier,
                assigned_reviewer, status, submitted_at, decided_at, version, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, 'rita.reviewer', ?, ?, ?, 1, ?)""",
            (
                counterparty_id,
                name,
                kind,
                country,
                registration,
                risk,
                status,
                submitted_at,
                decided_at,
                decided_at or submitted_at,
            ),
        )
        rating, rating_source = RATINGS[index - 1]
        evidence_rows = (
            (
                f"EV-{index * 2 - 1:03d}",
                counterparty_id,
                "financial_strength_opinion",
                rating_source,
                rating,
                _at(base, min(30, submitted_days + 2))[:10],
            ),
            (
                f"EV-{index * 2:03d}",
                counterparty_id,
                "observed_payout_history",
                f"Claims bordereau Q{3 if index % 2 else 2} 2026",
                PAYOUTS[index - 1],
                _at(base, min(30, submitted_days + 1))[:10],
            ),
        )
        conn.executemany(
            """INSERT INTO counterparty_evidence
               (id, counterparty_id, evidence_type, source, value, as_of)
               VALUES (?, ?, ?, ?, ?, ?)""",
            evidence_rows,
        )
        if decided_at:
            decision = "approve" if status == "approved" else "reject"
            _seed_audit(
                conn,
                at=decided_at,
                actor_username="rita.reviewer",
                actor_role="reviewer",
                module="counterparties",
                resource_type="counterparty",
                resource_id=counterparty_id,
                action=f"review_{decision}",
                reason=reason,
                before={"status": "pending_review"},
                after={"status": status},
            )


def _seed_claims(conn, base):
    amounts = (12900, 38450, 65500, 1975, 21200, 8400, 119900, 5775, 32900, 45800)
    currencies = ("GBP", "GBP", "USD", "EUR", "GBP", "USD", "EUR", "GBP", "USD", "EUR")
    reasons = {
        "approved": "The supporting documents and amount match the account record.",
        "rejected": "The submitted evidence did not meet the refund criteria.",
    }
    for index in range(25):
        claim_number = index + 1
        claim_id = f"CLM-{1000 + claim_number}"
        if index < 12:
            status = "submitted"
        elif index < 22:
            status = "approved"
        else:
            status = "rejected"
        submitted_days = 1 + ((index * 7) % 27)
        decision_lag = 1 + (index % 4)
        decided_at = _at(base, max(0, submitted_days - decision_lag)) if status != "submitted" else None
        claim_type = CLAIM_TYPES[index % len(CLAIM_TYPES)]
        counterparty_id = f"CP-{(index % len(COUNTERPARTIES)) + 1:03d}"
        amount_minor = amounts[index % len(amounts)] + ((index // len(amounts)) * 1250)
        currency = currencies[index % len(currencies)]
        conn.execute(
            """INSERT INTO claims
               (id, counterparty_id, claimant_ref, claim_type, description,
                amount_minor, currency, status, submitted_at, decided_at, version, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
            (
                claim_id,
                counterparty_id,
                f"CUST-{7000 + claim_number:04d}",
                claim_type,
                CLAIM_DESCRIPTIONS[index % len(CLAIM_DESCRIPTIONS)],
                amount_minor,
                currency,
                status,
                _at(base, submitted_days),
                decided_at,
                decided_at or _at(base, submitted_days),
            ),
        )
        if decided_at:
            decision = "approve" if status == "approved" else "reject"
            _seed_audit(
                conn,
                at=decided_at,
                actor_username="colin.claims",
                actor_role="claims_operator",
                module="claims",
                resource_type="claim",
                resource_id=claim_id,
                action=decision,
                reason=reasons[status],
                before={"status": "submitted"},
                after={"status": status},
            )


def _seed_flags(conn, base):
    for key, description, enabled, environment, owner_team, age, reason in FLAGS:
        updated_at = _at(base, age) if age is not None else _at(base)
        conn.execute(
            """INSERT INTO flags
               (key, description, enabled, environment, owner_team, version, updated_at)
               VALUES (?, ?, ?, ?, ?, 1, ?)""",
            (key, description, enabled, environment, owner_team, updated_at),
        )
        if age is not None:
            _seed_audit(
                conn,
                at=updated_at,
                actor_username="fiona.flags",
                actor_role="flag_operator",
                module="flags",
                resource_type="flag",
                resource_id=key,
                action="change_enabled",
                reason=reason,
                before={"enabled": not bool(enabled)},
                after={"enabled": bool(enabled)},
            )


def _seed_entitlements(conn, base):
    for index, item in enumerate(ENTITLEMENTS, start=1):
        employee, team, system, access_level, last_used_days, status, decision_age, reason = item
        last_used_at = _at(base, last_used_days, index % 8)
        decided_at = _at(base, decision_age) if decision_age is not None else None
        entitlement_id = f"ENT-{index:03d}"
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
                last_used_at,
                status,
                decided_at,
                decided_at or last_used_at,
            ),
        )
        if decided_at:
            _seed_audit(
                conn,
                at=decided_at,
                actor_username="nina.access",
                actor_role="access_reviewer",
                module="access_reviews",
                resource_type="entitlement",
                resource_id=entitlement_id,
                action="certify" if status == "certified" else "revoke",
                reason=reason,
                before={"status": "pending"},
                after={"status": status},
            )


def seed_if_empty(db_path):
    conn = connect(db_path)
    try:
        with transaction(conn):
            if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
                return False
            password = os.environ.get("DEMO_PASSWORD", "demo")
            base = datetime.now(timezone.utc)
            for username, display_name, role in DEMO_USERS:
                salt, digest = hash_password(password)
                conn.execute(
                    """INSERT INTO users
                       (username, display_name, role, password_salt, password_hash)
                       VALUES (?, ?, ?, ?, ?)""",
                    (username, display_name, role, salt, digest),
                )
            _seed_counterparties(conn, base)
            _seed_claims(conn, base)
            _seed_flags(conn, base)
            _seed_entitlements(conn, base)
        return True
    finally:
        conn.close()


def reset_db(db_path):
    init_db(db_path)
    conn = connect(db_path)
    try:
        with transaction(conn):
            conn.execute("DELETE FROM control_events")
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
