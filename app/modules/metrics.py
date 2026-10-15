from datetime import datetime, timedelta, timezone
from statistics import median

from fastapi import APIRouter, Depends

from app.core.auth import current_user, get_connection
from app.core.audit import list_audit


router = APIRouter()


def _parse_time(value):
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _median_hours(rows):
    durations = []
    for submitted_at, decided_at in rows:
        submitted = _parse_time(submitted_at)
        decided = _parse_time(decided_at)
        if submitted and decided:
            durations.append(max(0, (decided - submitted).total_seconds() / 3600))
    return round(median(durations), 1) if durations else 0


def collect_metrics(conn):
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=30)).isoformat()
    pending = conn.execute(
        "SELECT submitted_at FROM counterparties WHERE status = 'pending_review'"
    ).fetchall()
    oldest_days = max(
        (now - _parse_time(row["submitted_at"])).days for row in pending
    ) if pending else 0
    kyc_decisions = conn.execute(
        """SELECT submitted_at, decided_at FROM counterparties
           WHERE decided_at IS NOT NULL AND decided_at >= ?""",
        (cutoff,),
    ).fetchall()
    claims_decisions = conn.execute(
        """SELECT submitted_at, decided_at FROM claims
           WHERE decided_at IS NOT NULL AND decided_at >= ?""",
        (cutoff,),
    ).fetchall()
    open_values = {
        row["currency"]: row["total"]
        for row in conn.execute(
            """SELECT currency, SUM(amount_minor) AS total FROM claims
               WHERE status = 'submitted' GROUP BY currency ORDER BY currency"""
        ).fetchall()
    }
    flags_total = conn.execute("SELECT COUNT(*) FROM flags").fetchone()[0]
    flags_production = conn.execute(
        "SELECT COUNT(*) FROM flags WHERE environment = 'production'"
    ).fetchone()[0]
    changes_30d = conn.execute(
        "SELECT COUNT(*) FROM audit_events WHERE module = 'flags' AND at >= ?",
        (cutoff,),
    ).fetchone()[0]
    entitlements = {
        row["status"]: row["n"]
        for row in conn.execute(
            "SELECT status, COUNT(*) AS n FROM entitlements GROUP BY status"
        ).fetchall()
    }
    entitlement_total = sum(entitlements.values())
    completed = entitlements.get("certified", 0) + entitlements.get("revoked", 0)
    control_counts = {
        outcome: 0
        for outcome in (
            "forbidden",
            "stale_version",
            "invalid_transition",
            "validation_failed",
        )
    }
    control_counts.update(
        {
            row["outcome"]: row["n"]
            for row in conn.execute(
                """SELECT outcome, COUNT(*) AS n FROM control_events
                   WHERE at >= ? GROUP BY outcome""",
                (cutoff,),
            ).fetchall()
        }
    )
    return {
        "kyc": {
            "pending": len(pending),
            "oldest_pending_days": max(0, oldest_days),
            "decided_30d": len(kyc_decisions),
            "median_hours_to_decision": _median_hours(kyc_decisions),
        },
        "claims": {
            "open_count": conn.execute(
                "SELECT COUNT(*) FROM claims WHERE status = 'submitted'"
            ).fetchone()[0],
            "open_value_by_currency": open_values,
            "approved_30d": conn.execute(
                "SELECT COUNT(*) FROM claims WHERE status = 'approved' AND decided_at >= ?",
                (cutoff,),
            ).fetchone()[0],
            "median_hours_to_decision": _median_hours(claims_decisions),
        },
        "flags": {
            "total": flags_total,
            "production": flags_production,
            "changes_30d": changes_30d,
        },
        "access": {
            "quarter": "2026-Q4",
            "pending": entitlements.get("pending", 0),
            "certified": entitlements.get("certified", 0),
            "revoked": entitlements.get("revoked", 0),
            "completion_pct": round(100 * completed / entitlement_total, 1) if entitlement_total else 0,
        },
        "controls": control_counts,
        "imports_30d": conn.execute(
            "SELECT COUNT(*) FROM audit_events WHERE action = 'import' AND at >= ?",
            (cutoff,),
        ).fetchone()[0],
        "exports_30d": conn.execute(
            "SELECT COUNT(*) FROM audit_events WHERE action = 'export' AND at >= ?",
            (cutoff,),
        ).fetchone()[0],
    }


@router.get("/api/metrics")
def api_metrics(conn=Depends(get_connection), user=Depends(current_user)):
    return collect_metrics(conn)
