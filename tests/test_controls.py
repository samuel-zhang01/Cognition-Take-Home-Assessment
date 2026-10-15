import csv
import io
import json
import os
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.auth import clear_login_failures
from app.main import create_app
from app.seed import reset_db


ROOT = Path(__file__).resolve().parents[1]
COUNTERPARTY_SAMPLE = ROOT / "samples" / "counterparties_q4_onboarding.csv"
CLAIMS_SAMPLE = ROOT / "samples" / "claims_batch_with_errors.csv"


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "portal.db"


@pytest.fixture
def app(db_path):
    return create_app(db_path=db_path)


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


def login(client, username):
    clear_login_failures(username, "testclient")
    response = client.post(
        "/login",
        data={"username": username, "password": os.environ.get("DEMO_PASSWORD", "demo")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    return client


def db_rows(db_path, query, params=()):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in conn.execute(query, params).fetchall()]
    finally:
        conn.close()


def upload_csv(client, module, path, dry_run, reason="Quarterly onboarding batch"):
    return client.post(
        f"/api/import/{module}",
        files={"file": (path.name, path.read_bytes(), "text/csv")},
        data={"reason": reason, "dry_run": str(dry_run).lower()},
    )


def upload_csv_content(client, module, filename, content, dry_run=True):
    return client.post(
        f"/api/import/{module}",
        files={"file": (filename, content, "text/csv")},
        data={"reason": "Import validation test", "dry_run": str(dry_run).lower()},
    )


def test_each_role_can_make_its_happy_path_change_and_auditor_sees_it(client):
    reviewer = login(client, "rita.reviewer")
    response = reviewer.post(
        "/api/counterparties/CP-001/review",
        json={"decision": "approve", "reason": "Evidence reviewed", "expected_version": 1},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"

    claims_operator = login(TestClient(client.app), "colin.claims")
    response = claims_operator.post(
        "/api/claims/CLM-1001/decide",
        json={"decision": "approve", "reason": "Test claim is complete", "expected_version": 1},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"

    flag_operator = login(TestClient(client.app), "fiona.flags")
    response = flag_operator.post(
        "/api/flags/claims.fast_track_travel/change",
        json={"enabled": True, "reason": "Enable travel review", "expected_version": 1},
    )
    assert response.status_code == 200
    assert response.json()["enabled"] == 1

    auditor = login(TestClient(client.app), "aaron.auditor")
    for resource_id, actor, module in (
        ("CP-001", "rita.reviewer", "counterparties"),
        ("CLM-1001", "colin.claims", "claims"),
        ("claims.fast_track_travel", "fiona.flags", "flags"),
    ):
        events = auditor.get(f"/api/audit?resource_id={resource_id}").json()
        assert any(
            item["actor_username"] == actor and item["module"] == module
            for item in events
        )
    claim_event = auditor.get("/api/audit?resource_id=CLM-1001").json()[0]
    assert claim_event["action"] == "approve"


def test_forbidden_mutations_leave_state_and_audit_unchanged_and_record_controls(
    app, client, db_path
):
    auditor = login(client, "aaron.auditor")
    mutations = [
        (
            "/api/counterparties/CP-001/review",
            {"decision": "approve", "reason": "Denied", "expected_version": 1},
        ),
        (
            "/api/claims/CLM-1001/decide",
            {"decision": "approve", "reason": "Denied", "expected_version": 1},
        ),
        (
            "/api/flags/claims.fast_track_travel/change",
            {"enabled": True, "reason": "Denied", "expected_version": 1},
        ),
    ]
    before_audit = db_rows(db_path, "SELECT COUNT(*) AS n FROM audit_events")[0]["n"]
    before_controls = db_rows(db_path, "SELECT COUNT(*) AS n FROM control_events")[0]["n"]
    for path, body in mutations:
        assert auditor.post(path, json=body).status_code == 403
    assert db_rows(db_path, "SELECT status, version FROM counterparties WHERE id='CP-001'")[0] == {
        "status": "pending_review",
        "version": 1,
    }
    assert db_rows(db_path, "SELECT status, version FROM claims WHERE id='CLM-1001'")[0] == {
        "status": "submitted",
        "version": 1,
    }
    assert db_rows(
        db_path, "SELECT enabled, version FROM flags WHERE key='claims.fast_track_travel'"
    )[0] == {"enabled": 0, "version": 1}
    assert db_rows(db_path, "SELECT COUNT(*) AS n FROM audit_events")[0]["n"] == before_audit
    denied = db_rows(
        db_path,
        "SELECT outcome FROM control_events WHERE outcome='forbidden' ORDER BY id",
    )
    assert len(denied) == 3
    assert db_rows(db_path, "SELECT COUNT(*) AS n FROM control_events")[0]["n"] == before_controls + 3

    reviewer = login(TestClient(app), "rita.reviewer")
    assert reviewer.post(mutations[1][0], json=mutations[1][1]).status_code == 403
    claims_operator = login(TestClient(app), "colin.claims")
    assert claims_operator.post(mutations[2][0], json=mutations[2][1]).status_code == 403
    assert db_rows(
        db_path, "SELECT COUNT(*) AS n FROM control_events WHERE outcome='forbidden'"
    )[0]["n"] == 5


def test_forged_identity_is_ignored_and_missing_session_is_unauthorized(client, db_path):
    claims_operator = login(client, "colin.claims")
    response = claims_operator.post(
        "/api/claims/CLM-1001/decide",
        json={
            "decision": "approve",
            "reason": "Claim approved after review",
            "expected_version": 1,
            "actor": "aaron.auditor",
            "role": "auditor",
            "user": "aaron.auditor",
        },
    )
    assert response.status_code == 200
    event = db_rows(
        db_path,
        "SELECT actor_username, actor_role, action FROM audit_events WHERE resource_id='CLM-1001'",
    )[0]
    assert event == {
        "actor_username": "colin.claims",
        "actor_role": "claims_operator",
        "action": "approve",
    }

    unauthenticated = TestClient(client.app)
    assert unauthenticated.get("/api/me").status_code == 401
    assert unauthenticated.post(
        "/api/claims/CLM-1002/decide",
        json={"decision": "reject", "reason": "No session", "expected_version": 1},
    ).status_code == 401
    assert db_rows(db_path, "SELECT COUNT(*) AS n FROM control_events")[0]["n"] == 0

    auditor = login(TestClient(client.app), "aaron.auditor")
    response = auditor.post(
        "/api/counterparties/CP-001/review",
        json={
            "decision": "approve",
            "reason": "Forged role should not work",
            "expected_version": 1,
            "role": "reviewer",
        },
    )
    assert response.status_code == 403
    assert db_rows(
        db_path, "SELECT outcome FROM control_events ORDER BY id"
    ) == [{"outcome": "forbidden"}]


def test_reasons_transitions_and_stale_versions_never_write_extra_audits(client, db_path):
    claims_operator = login(client, "colin.claims")
    endpoint = "/api/claims/CLM-1001/decide"
    before_audit = db_rows(db_path, "SELECT COUNT(*) AS n FROM audit_events")[0]["n"]
    assert claims_operator.post(
        endpoint, json={"decision": "approve", "expected_version": 1}
    ).status_code == 422
    assert claims_operator.post(
        endpoint,
        json={"decision": "approve", "reason": "   ", "expected_version": 1},
    ).status_code == 422
    assert db_rows(db_path, "SELECT COUNT(*) AS n FROM audit_events")[0]["n"] == before_audit

    assert claims_operator.post(
        endpoint,
        json={"decision": "approve", "reason": "Valid approval reason", "expected_version": 1},
    ).status_code == 200
    audit_count = db_rows(db_path, "SELECT COUNT(*) AS n FROM audit_events")[0]["n"]
    assert claims_operator.post(
        endpoint,
        json={"decision": "approve", "reason": "Approve again", "expected_version": 2},
    ).status_code == 409
    assert claims_operator.post(
        endpoint,
        json={"decision": "approve", "reason": "Stale attempt", "expected_version": 1},
    ).status_code == 409

    reviewer = login(TestClient(client.app), "rita.reviewer")
    review_endpoint = "/api/counterparties/CP-001/review"
    assert reviewer.post(
        review_endpoint,
        json={"decision": "reject", "reason": "Valid counterparty decision", "expected_version": 1},
    ).status_code == 200
    assert reviewer.post(
        review_endpoint,
        json={"decision": "approve", "reason": "Decide again", "expected_version": 2},
    ).status_code == 409

    flag_operator = login(TestClient(client.app), "fiona.flags")
    flag_endpoint = "/api/flags/claims.fast_track_travel/change"
    assert flag_operator.post(
        flag_endpoint,
        json={"enabled": False, "reason": "Already disabled", "expected_version": 1},
    ).status_code == 409
    assert db_rows(db_path, "SELECT COUNT(*) AS n FROM audit_events")[0]["n"] == audit_count + 1
    assert db_rows(db_path, "SELECT version FROM claims WHERE id='CLM-1001'")[0]["version"] == 2
    outcomes = {
        row["outcome"]
        for row in db_rows(db_path, "SELECT outcome FROM control_events")
    }
    assert outcomes == {"validation_failed", "invalid_transition", "stale_version"}


def test_stale_command_records_one_control_event_without_audit_change(client, db_path):
    claims_operator = login(client, "colin.claims")
    before_audit = db_rows(db_path, "SELECT COUNT(*) AS n FROM audit_events")[0]["n"]
    before_controls = db_rows(db_path, "SELECT COUNT(*) AS n FROM control_events")[0]["n"]
    response = claims_operator.post(
        "/api/claims/CLM-1001/decide",
        json={"decision": "reject", "reason": "Stale version test", "expected_version": 8},
    )
    assert response.status_code == 409
    assert response.json()["error"] == "stale_version"
    assert db_rows(db_path, "SELECT COUNT(*) AS n FROM audit_events")[0]["n"] == before_audit
    assert db_rows(db_path, "SELECT COUNT(*) AS n FROM control_events")[0]["n"] == before_controls + 1
    assert db_rows(
        db_path,
        "SELECT outcome, resource_id FROM control_events ORDER BY id DESC LIMIT 1",
    )[0] == {"outcome": "stale_version", "resource_id": "CLM-1001"}


def test_same_starting_version_writes_only_once(client, app, db_path):
    body = {"decision": "approve", "reason": "Single winning review", "expected_version": 1}
    path = "/api/counterparties/CP-002/review"
    reviewer = login(client, "rita.reviewer")
    assert reviewer.post(path, json=body).status_code == 200
    assert reviewer.post(path, json=body).status_code == 409
    assert db_rows(
        db_path, "SELECT COUNT(*) AS n FROM audit_events WHERE resource_id='CP-002'"
    )[0]["n"] == 1

    threaded_app = create_app(db_path=db_path.parent / "threaded.db")
    clients = [
        login(TestClient(threaded_app), "rita.reviewer"),
        login(TestClient(threaded_app), "rita.reviewer"),
    ]
    barrier = threading.Barrier(2)

    def write(test_client):
        barrier.wait()
        return test_client.post(
            "/api/counterparties/CP-001/review",
            json={"decision": "approve", "reason": "Concurrent review", "expected_version": 1},
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(write, clients))
    assert sorted(statuses) == [200, 409]
    assert db_rows(
        db_path.parent / "threaded.db",
        "SELECT COUNT(*) AS n FROM audit_events WHERE resource_id='CP-001'",
    )[0]["n"] == 1


def test_restart_preserves_state_and_reset_reseeds(db_path):
    first_app = create_app(db_path=db_path)
    with TestClient(first_app) as first:
        reviewer = login(first, "rita.reviewer")
        assert reviewer.post(
            "/api/counterparties/CP-001/review",
            json={"decision": "approve", "reason": "Preserve this decision", "expected_version": 1},
        ).status_code == 200
    before_restart = db_rows(db_path, "SELECT COUNT(*) AS n FROM audit_events")[0]["n"]

    second_app = create_app(db_path=db_path)
    with TestClient(second_app) as second:
        login(second, "rita.reviewer")
        assert second.get("/api/counterparties/CP-001").json()["status"] == "approved"
        assert db_rows(db_path, "SELECT COUNT(*) AS n FROM audit_events")[0]["n"] == before_restart

    assert reset_db(db_path)
    third_app = create_app(db_path=db_path)
    with TestClient(third_app) as third:
        login(third, "rita.reviewer")
        assert third.get("/api/counterparties/CP-001").json()["status"] == "pending_review"
        counterparty_events = third.get("/api/audit?module=counterparties").json()
        assert counterparty_events
        assert all(event["module"] == "counterparties" for event in counterparty_events)


def test_claim_counterparty_linkage_and_audit_scope(client):
    reviewer = login(client, "rita.reviewer")
    linked = reviewer.get("/api/counterparties/CP-001").json()["claims"]
    assert {claim["id"] for claim in linked} == {"CLM-1001", "CLM-1013", "CLM-1025"}
    assert reviewer.get("/api/claims/CLM-1001").json()["counterparty_id"] == "CP-001"

    reviewer.post(
        "/api/counterparties/CP-001/review",
        json={"decision": "approve", "reason": "Scoped event test", "expected_version": 1},
    )
    claims_operator = login(TestClient(client.app), "colin.claims")
    claims_operator.post(
        "/api/claims/CLM-1001/decide",
        json={"decision": "approve", "reason": "Claims event test", "expected_version": 1},
    )
    scoped = reviewer.get("/api/audit").json()
    assert scoped and all(event["module"] == "counterparties" for event in scoped)
    assert reviewer.get("/api/audit?module=claims").json() == []


def test_access_reviews_decision_permissions_and_stale_version(client, db_path):
    nina = login(client, "nina.access")
    path = "/api/access-reviews/ENT-002/decide"
    body = {"decision": "certify", "reason": "Access confirmed with manager", "expected_version": 1}
    assert nina.post(path, json=body).status_code == 200
    assert nina.get("/api/access-reviews?status=certified").json()
    certified = db_rows(
        db_path, "SELECT status, decided_at, version FROM entitlements WHERE id='ENT-002'"
    )[0]
    assert certified["status"] == "certified"
    assert certified["decided_at"]
    assert certified["version"] == 2
    assert nina.post(path, json=body).status_code == 409
    revoke = nina.post(
        path,
        json={
            "decision": "revoke",
            "reason": "The entitlement is no longer needed",
            "expected_version": certified["version"],
        },
    )
    assert revoke.status_code == 409
    assert revoke.json()["error"] == "invalid_transition"
    assert db_rows(
        db_path, "SELECT status FROM entitlements WHERE id='ENT-002'"
    )[0]["status"] == "certified"

    reviewer = login(TestClient(client.app), "rita.reviewer")
    assert reviewer.post(path, json=body).status_code == 403
    access_events = db_rows(
        db_path,
        "SELECT actor_username, action FROM audit_events WHERE module='access_reviews' AND resource_id='ENT-002'",
    )
    assert access_events == [{"actor_username": "nina.access", "action": "certify"}]


def test_claim_reject_records_decision_and_audit(client, db_path):
    claims_operator = login(client, "colin.claims")
    response = claims_operator.post(
        "/api/claims/CLM-1002/decide",
        json={"decision": "reject", "reason": "Evidence does not meet policy", "expected_version": 1},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert response.json()["decided_at"]
    event = db_rows(
        db_path, "SELECT action, actor_username FROM audit_events WHERE resource_id='CLM-1002'"
    )[0]
    assert event == {"action": "reject", "actor_username": "colin.claims"}


def test_import_dry_run_reports_sample_errors_and_writes_nothing(client, db_path):
    claims_operator = login(client, "colin.claims")
    before_claims = db_rows(db_path, "SELECT COUNT(*) AS n FROM claims")[0]["n"]
    before_audit = db_rows(db_path, "SELECT COUNT(*) AS n FROM audit_events")[0]["n"]
    before_controls = db_rows(db_path, "SELECT COUNT(*) AS n FROM control_events")[0]["n"]
    response = upload_csv(claims_operator, "claims", CLAIMS_SAMPLE, dry_run=True)
    assert response.status_code == 200
    result = response.json()
    assert result["rows"] == 5
    assert result["valid"] == 3
    assert result["committed"] is False
    assert len(result["errors"]) == 2
    assert {error["column"] for error in result["errors"]} == {"counterparty_id", "amount"}
    assert db_rows(db_path, "SELECT COUNT(*) AS n FROM claims")[0]["n"] == before_claims
    assert db_rows(db_path, "SELECT COUNT(*) AS n FROM audit_events")[0]["n"] == before_audit
    assert db_rows(db_path, "SELECT COUNT(*) AS n FROM control_events")[0]["n"] == before_controls


@pytest.mark.parametrize("amount", ["10.009", "NaN", "Infinity"])
def test_claim_import_rejects_fractional_cents_and_nonfinite_amounts(client, amount):
    claims_operator = login(client, "colin.claims")
    content = (
        "id,counterparty_id,claimant_ref,claim_type,description,amount,currency,submitted_at\n"
        f"CLM-BAD-AMOUNT,CP-001,CUST-9999,merchant dispute,Test claim,{amount},GBP,2026-10-15\n"
    )
    response = upload_csv_content(
        claims_operator, "claims", "bad-amount.csv", content
    )
    assert response.status_code == 200
    result = response.json()
    assert result["committed"] is False
    assert result["valid"] == 0
    assert any(
        error["row"] == 2 and error["column"] == "amount"
        for error in result["errors"]
    )


def test_claim_import_converts_decimal_amount_to_minor_units_exactly(client, db_path):
    claims_operator = login(client, "colin.claims")
    content = (
        "id,counterparty_id,claimant_ref,claim_type,description,amount,currency,submitted_at\n"
        "CLM-EXACT-AMOUNT,CP-001,CUST-9998,merchant dispute,Test claim,10.01,GBP,2026-10-15\n"
    )
    response = upload_csv_content(
        claims_operator, "claims", "exact-amount.csv", content, dry_run=False
    )
    assert response.status_code == 200
    assert response.json() == {
        "rows": 1,
        "valid": 1,
        "errors": [],
        "committed": True,
    }
    assert db_rows(
        db_path,
        "SELECT amount_minor FROM claims WHERE id='CLM-EXACT-AMOUNT'",
    )[0]["amount_minor"] == 1001


def test_import_rejects_unknown_columns_and_extra_csv_fields(client, db_path):
    reviewer = login(client, "rita.reviewer")
    before_counterparties = db_rows(
        db_path, "SELECT COUNT(*) AS n FROM counterparties"
    )[0]["n"]
    headers = (
        "id,name,kind,country,registration_number,risk_tier,assigned_reviewer,submitted_at"
    )
    row = "CP-IMPORT-EXTRA,Example Mutual,insurer,United Kingdom,GB-100,low,rita.reviewer,2026-10-15"

    unknown_column = upload_csv_content(
        reviewer,
        "counterparties",
        "unknown-column.csv",
        f"{headers},unexpected\n{row},extra\n",
    ).json()
    assert any(
        error["row"] == 1 and error["column"] == "unexpected"
        for error in unknown_column["errors"]
    )
    assert unknown_column["committed"] is False

    extra_field = upload_csv_content(
        reviewer,
        "counterparties",
        "extra-field.csv",
        f"{headers}\n{row},extra\n",
    ).json()
    assert any(
        error["row"] == 2 and error["column"] == "row"
        for error in extra_field["errors"]
    )
    assert extra_field["committed"] is False
    assert db_rows(
        db_path, "SELECT COUNT(*) AS n FROM counterparties"
    )[0]["n"] == before_counterparties


def test_valid_import_commits_all_rows_and_one_audit_event(client, db_path):
    reviewer = login(client, "rita.reviewer")
    before_counterparties = db_rows(db_path, "SELECT COUNT(*) AS n FROM counterparties")[0]["n"]
    before_audit = db_rows(db_path, "SELECT COUNT(*) AS n FROM audit_events")[0]["n"]
    response = upload_csv(reviewer, "counterparties", COUNTERPARTY_SAMPLE, dry_run=False)
    assert response.status_code == 200
    result = response.json()
    assert result == {"rows": 3, "valid": 3, "errors": [], "committed": True}
    assert db_rows(db_path, "SELECT COUNT(*) AS n FROM counterparties")[0]["n"] == before_counterparties + 3
    assert db_rows(db_path, "SELECT COUNT(*) AS n FROM audit_events")[0]["n"] == before_audit + 1
    event = db_rows(
        db_path,
        "SELECT actor_username, module, resource_type, resource_id, action, reason, details "
        "FROM audit_events WHERE action='import'",
    )[0]
    assert event["actor_username"] == "rita.reviewer"
    assert event["module"] == "counterparties"
    assert event["resource_type"] == "dataset"
    assert event["resource_id"] == "counterparties"
    assert event["action"] == "import"
    assert event["reason"] == "Quarterly onboarding batch"
    assert json.loads(event["details"]) == {
        "filename": COUNTERPARTY_SAMPLE.name,
        "rows": 3,
    }
    assert db_rows(
        db_path, "SELECT version, status FROM counterparties WHERE id='CP-ONB-101'"
    )[0] == {"version": 1, "status": "pending_review"}


def test_invalid_non_dry_run_import_commits_nothing_and_records_control(client, db_path):
    claims_operator = login(client, "colin.claims")
    before_claims = db_rows(db_path, "SELECT COUNT(*) AS n FROM claims")[0]["n"]
    before_audit = db_rows(db_path, "SELECT COUNT(*) AS n FROM audit_events")[0]["n"]
    before_controls = db_rows(db_path, "SELECT COUNT(*) AS n FROM control_events")[0]["n"]
    response = upload_csv(claims_operator, "claims", CLAIMS_SAMPLE, dry_run=False)
    assert response.status_code == 200
    assert response.json()["committed"] is False
    assert len(response.json()["errors"]) == 2
    assert db_rows(db_path, "SELECT COUNT(*) AS n FROM claims")[0]["n"] == before_claims
    assert db_rows(db_path, "SELECT COUNT(*) AS n FROM audit_events")[0]["n"] == before_audit
    assert db_rows(db_path, "SELECT COUNT(*) AS n FROM control_events")[0]["n"] == before_controls + 1
    assert db_rows(
        db_path, "SELECT outcome FROM control_events ORDER BY id DESC LIMIT 1"
    )[0]["outcome"] == "validation_failed"


def test_wrong_role_import_returns_forbidden_and_records_control(client, db_path):
    flag_operator = login(client, "fiona.flags")
    before_controls = db_rows(db_path, "SELECT COUNT(*) AS n FROM control_events")[0]["n"]
    before_audit = db_rows(db_path, "SELECT COUNT(*) AS n FROM audit_events")[0]["n"]
    response = upload_csv(flag_operator, "counterparties", COUNTERPARTY_SAMPLE, dry_run=False)
    assert response.status_code == 403
    assert response.json()["error"] == "forbidden"
    assert db_rows(db_path, "SELECT COUNT(*) AS n FROM control_events")[0]["n"] == before_controls + 1
    assert db_rows(db_path, "SELECT COUNT(*) AS n FROM audit_events")[0]["n"] == before_audit
    assert db_rows(
        db_path, "SELECT module, outcome FROM control_events ORDER BY id DESC LIMIT 1"
    )[0] == {"module": "counterparties", "outcome": "forbidden"}


def test_claims_operator_audit_export_is_scoped_and_audited(client, db_path):
    claims_operator = login(client, "colin.claims")
    before_audit = db_rows(db_path, "SELECT COUNT(*) AS n FROM audit_events")[0]["n"]
    response = claims_operator.get("/api/export/audit.csv")
    assert response.status_code == 200
    exported = list(csv.DictReader(io.StringIO(response.text)))
    assert exported and all(row["module"] == "claims" for row in exported)
    assert db_rows(db_path, "SELECT COUNT(*) AS n FROM audit_events")[0]["n"] == before_audit + 1
    export_event = db_rows(
        db_path,
        "SELECT actor_username, module, action, details FROM audit_events "
        "WHERE module='audit' AND actor_username='colin.claims' ORDER BY id DESC LIMIT 1",
    )[0]
    assert export_event["action"] == "export"
    assert json.loads(export_event["details"]) == {
        "format": "csv",
        "rows": len(exported),
    }
    auditor = login(TestClient(client.app), "aaron.auditor")
    visible_export_events = auditor.get("/api/audit?module=audit").json()
    assert any(
        event["actor_username"] == "colin.claims" and event["resource_id"] == "audit"
        for event in visible_export_events
    )


def test_metrics_shape_and_claim_values_remain_separated_by_currency(client, db_path):
    user = login(client, "nina.access")
    response = user.get("/api/metrics")
    assert response.status_code == 200
    metrics = response.json()
    assert set(metrics) == {
        "kyc", "claims", "flags", "access", "controls", "imports_30d", "exports_30d"
    }
    assert set(metrics["kyc"]) == {
        "pending", "oldest_pending_days", "decided_30d", "median_hours_to_decision"
    }
    assert set(metrics["claims"]) == {
        "open_count", "open_value_by_currency", "approved_30d", "median_hours_to_decision"
    }
    assert set(metrics["flags"]) == {"total", "production", "changes_30d"}
    assert set(metrics["access"]) == {
        "quarter", "pending", "certified", "revoked", "completion_pct"
    }
    assert set(metrics["controls"]) == {
        "forbidden", "stale_version", "invalid_transition", "validation_failed"
    }
    expected_values = {
        row["currency"]: row["amount"]
        for row in db_rows(
            db_path,
            """SELECT currency, SUM(amount_minor) AS amount FROM claims
               WHERE status='submitted' GROUP BY currency""",
        )
    }
    assert metrics["claims"]["open_value_by_currency"] == expected_values
    assert set(expected_values) == {"EUR", "GBP", "USD"}
    assert "total" not in metrics["claims"]["open_value_by_currency"]


def test_flags_export_does_not_increase_flag_change_metric(client):
    flag_operator = login(client, "fiona.flags")
    before = flag_operator.get("/api/metrics").json()["flags"]["changes_30d"]
    assert flag_operator.get("/api/export/flags.csv").status_code == 200
    after_export = flag_operator.get("/api/metrics").json()["flags"]["changes_30d"]
    assert after_export == before
    changed = flag_operator.post(
        "/api/flags/claims.fast_track_travel/change",
        json={
            "enabled": True,
            "reason": "Enable the reviewed travel workflow",
            "expected_version": 1,
        },
    )
    assert changed.status_code == 200
    assert flag_operator.get("/api/metrics").json()["flags"]["changes_30d"] == before + 1
