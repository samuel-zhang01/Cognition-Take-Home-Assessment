import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.seed import reset_db


USERS = (
    "rita.reviewer",
    "colin.claims",
    "fiona.flags",
    "aaron.auditor",
)


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
    response = client.post(
        "/login", data={"username": username, "password": "demo"}, follow_redirects=False
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
        "/api/claims/CLM-1001/approve",
        json={"reason": "Test claim is complete", "expected_version": 1},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved_simulated"

    flag_operator = login(TestClient(client.app), "fiona.flags")
    response = flag_operator.post(
        "/api/flags/sandbox.new_claims_intake_form/change",
        json={"enabled": True, "reason": "Enable sandbox preview", "expected_version": 1},
    )
    assert response.status_code == 200
    assert response.json()["enabled"] == 1

    auditor = login(TestClient(client.app), "aaron.auditor")
    events = auditor.get("/api/audit").json()
    assert {
        (item["actor_username"], item["module"]) for item in events
    } == {
        ("rita.reviewer", "counterparties"),
        ("colin.claims", "claims"),
        ("fiona.flags", "flags"),
    }


def test_forbidden_mutations_do_not_change_state_or_audit(app, client, db_path):
    auditor = login(client, "aaron.auditor")
    mutations = [
        (
            "/api/counterparties/CP-001/review",
            {"decision": "approve", "reason": "Denied", "expected_version": 1},
        ),
        (
            "/api/claims/CLM-1001/approve",
            {"reason": "Denied", "expected_version": 1},
        ),
        (
            "/api/flags/sandbox.new_claims_intake_form/change",
            {"enabled": True, "reason": "Denied", "expected_version": 1},
        ),
    ]
    before = db_rows(db_path, "SELECT COUNT(*) AS n FROM audit_events")[0]["n"]
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
    assert db_rows(db_path, "SELECT enabled, version FROM flags WHERE key=?", ("sandbox.new_claims_intake_form",))[0] == {
        "enabled": 0,
        "version": 1,
    }
    assert db_rows(db_path, "SELECT COUNT(*) AS n FROM audit_events")[0]["n"] == before

    reviewer = login(TestClient(app), "rita.reviewer")
    assert reviewer.post(
        mutations[1][0], json=mutations[1][1]
    ).status_code == 403
    claims_operator = login(TestClient(app), "colin.claims")
    assert claims_operator.post(
        mutations[2][0], json=mutations[2][1]
    ).status_code == 403


def test_forged_identity_is_ignored_and_missing_session_is_unauthorized(client, db_path):
    claims_operator = login(client, "colin.claims")
    response = claims_operator.post(
        "/api/claims/CLM-1001/approve",
        json={
            "reason": "Claim approved after review",
            "expected_version": 1,
            "actor": "aaron.auditor",
            "role": "auditor",
            "user": "aaron.auditor",
        },
    )
    assert response.status_code == 200
    event = db_rows(db_path, "SELECT actor_username, actor_role FROM audit_events")[0]
    assert event == {"actor_username": "colin.claims", "actor_role": "claims_operator"}

    unauthenticated = TestClient(client.app)
    assert unauthenticated.get("/api/me").status_code == 401
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


def test_reasons_transitions_and_stale_versions_never_write_extra_audits(client, db_path):
    claims_operator = login(client, "colin.claims")
    endpoint = "/api/claims/CLM-1001/approve"
    assert claims_operator.post(endpoint, json={"expected_version": 1}).status_code == 422
    assert claims_operator.post(
        endpoint, json={"reason": "   ", "expected_version": 1}
    ).status_code == 422
    assert db_rows(db_path, "SELECT COUNT(*) AS n FROM audit_events")[0]["n"] == 0

    assert claims_operator.post(
        endpoint, json={"reason": "Valid approval reason", "expected_version": 1}
    ).status_code == 200
    audit_count = db_rows(db_path, "SELECT COUNT(*) AS n FROM audit_events")[0]["n"]
    assert claims_operator.post(
        endpoint, json={"reason": "Approve again", "expected_version": 2}
    ).status_code == 409
    assert claims_operator.post(
        endpoint, json={"reason": "Stale attempt", "expected_version": 1}
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
    flag_endpoint = "/api/flags/sandbox.new_claims_intake_form/change"
    assert flag_operator.post(
        flag_endpoint,
        json={"enabled": False, "reason": "Already disabled", "expected_version": 1},
    ).status_code == 409
    assert db_rows(db_path, "SELECT COUNT(*) AS n FROM audit_events")[0]["n"] == audit_count + 1
    assert db_rows(db_path, "SELECT version FROM claims WHERE id='CLM-1001'")[0]["version"] == 2


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

    second_app = create_app(db_path=db_path)
    with TestClient(second_app) as second:
        login(second, "rita.reviewer")
        assert second.get("/api/counterparties/CP-001").json()["status"] == "approved"
        assert len(second.get("/api/audit").json()) == 1

    assert reset_db(db_path)
    third_app = create_app(db_path=db_path)
    with TestClient(third_app) as third:
        login(third, "rita.reviewer")
        assert third.get("/api/counterparties/CP-001").json()["status"] == "pending_review"
        assert third.get("/api/audit").json() == []


def test_claim_counterparty_linkage_and_audit_scope(client):
    reviewer = login(client, "rita.reviewer")
    linked = reviewer.get("/api/counterparties/CP-001").json()["claims"]
    assert {claim["id"] for claim in linked} == {"CLM-1001", "CLM-1002"}
    assert reviewer.get("/api/claims/CLM-1001").json()["counterparty_id"] == "CP-001"

    reviewer.post(
        "/api/counterparties/CP-001/review",
        json={"decision": "approve", "reason": "Scoped event test", "expected_version": 1},
    )
    claims_operator = login(TestClient(client.app), "colin.claims")
    claims_operator.post(
        "/api/claims/CLM-1001/approve",
        json={"reason": "Claims event test", "expected_version": 1},
    )
    scoped = reviewer.get("/api/audit").json()
    assert scoped and all(event["module"] == "counterparties" for event in scoped)
    assert reviewer.get("/api/audit?module=claims").json() == []
