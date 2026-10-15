import os
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.core.auth import hash_password
from app.core.db import init_db
from app.main import create_app
from app.seed import reset_db


def create_legacy_database(db_path):
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                role TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                password_hash TEXT NOT NULL
            );
            CREATE TABLE sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL
            );
            CREATE TABLE counterparties (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                kind TEXT NOT NULL,
                market TEXT NOT NULL,
                status TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE counterparty_evidence (
                id TEXT PRIMARY KEY,
                counterparty_id TEXT NOT NULL REFERENCES counterparties(id) ON DELETE CASCADE,
                evidence_type TEXT NOT NULL,
                source TEXT NOT NULL,
                source_type TEXT NOT NULL,
                rated_entity_or_market TEXT NOT NULL,
                value TEXT NOT NULL,
                as_of TEXT NOT NULL,
                provenance TEXT NOT NULL
            );
            CREATE TABLE claims (
                id TEXT PRIMARY KEY,
                counterparty_id TEXT NOT NULL REFERENCES counterparties(id),
                claimant_ref TEXT NOT NULL,
                description TEXT NOT NULL,
                amount_minor INTEGER NOT NULL,
                currency TEXT NOT NULL,
                status TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE flags (
                key TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                enabled INTEGER NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                at TEXT NOT NULL,
                actor_user_id INTEGER NOT NULL REFERENCES users(id),
                actor_role TEXT NOT NULL,
                module TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                action TEXT NOT NULL,
                reason TEXT NOT NULL,
                before_json TEXT NOT NULL,
                after_json TEXT NOT NULL,
                resource_version INTEGER NOT NULL
            );
            """
        )
        password = os.environ.get("DEMO_PASSWORD", "demo")
        salt, digest = hash_password(password)
        updated_at = "2025-10-20T12:00:00+00:00"
        conn.execute(
            """INSERT INTO users
               (username, display_name, role, password_salt, password_hash)
               VALUES (?, ?, ?, ?, ?)""",
            ("rita.reviewer", "Rita Patel", "reviewer", salt, digest),
        )
        conn.execute(
            """INSERT INTO counterparties
               (id, name, kind, market, status, version, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                "CP-LEGACY",
                "Legacy Mutual",
                "insurer",
                "UK",
                "approved",
                1,
                updated_at,
            ),
        )
        conn.execute(
            """INSERT INTO counterparty_evidence
               (id, counterparty_id, evidence_type, source, source_type,
                rated_entity_or_market, value, as_of, provenance)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "EV-LEGACY",
                "CP-LEGACY",
                "financial_strength_opinion",
                "Kestrel Ratings",
                "credit_rating",
                "Legacy Mutual",
                "A-, stable outlook",
                "2025-10-20",
                "Legacy evidence record",
            ),
        )
        conn.execute(
            """INSERT INTO claims
               (id, counterparty_id, claimant_ref, description, amount_minor,
                currency, status, version, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "CLM-LEGACY",
                "CP-LEGACY",
                "CUST-1001",
                "Legacy claim",
                1000,
                "GBP",
                "approved_simulated",
                1,
                updated_at,
            ),
        )
        conn.execute(
            """INSERT INTO flags (key, description, enabled, version, updated_at)
               VALUES (?, ?, ?, ?, ?)""",
            ("sandbox.old_flag", "Legacy flag", 1, 1, updated_at),
        )
        actor_user_id = conn.execute(
            "SELECT id FROM users WHERE username='rita.reviewer'"
        ).fetchone()[0]
        conn.execute(
            """INSERT INTO audit_events
               (at, actor_user_id, actor_role, module, resource_type, resource_id,
                action, reason, before_json, after_json, resource_version)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                updated_at,
                actor_user_id,
                "reviewer",
                "counterparties",
                "counterparty",
                "CP-LEGACY",
                "approve",
                "Legacy audit record",
                "{}",
                "{}",
                1,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def test_startup_migrates_legacy_schema_and_preserves_data(tmp_path):
    db_path = tmp_path / "legacy-portal.db"
    create_legacy_database(db_path)
    assert init_db(db_path) is None

    application = create_app(db_path=db_path)
    with TestClient(application) as client:
        login = client.post(
            "/login",
            data={
                "username": "rita.reviewer",
                "password": os.environ.get("DEMO_PASSWORD", "demo"),
            },
            follow_redirects=False,
        )
        assert login.status_code == 303
        assert client.get("/api/metrics").status_code == 200
        assert client.get("/counterparties/CP-LEGACY").status_code == 200
        imported = client.post(
            "/api/import/counterparties",
            files={
                "file": (
                    "legacy-import.csv",
                    (
                        "id,name,kind,country,registration_number,risk_tier,"
                        "assigned_reviewer,submitted_at\n"
                        "CP-IMPORTED,Imported Mutual,insurer,United Kingdom,"
                        "UK-REG-900,low,rita.reviewer,2026-10-15\n"
                    ),
                    "text/csv",
                )
            },
            data={"reason": "Legacy migration regression", "dry_run": "false"},
        )
        assert imported.status_code == 200
        assert imported.json() == {
            "rows": 1,
            "valid": 1,
            "errors": [],
            "committed": True,
        }

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        counterparty = conn.execute(
            "SELECT * FROM counterparties WHERE id='CP-LEGACY'"
        ).fetchone()
        assert counterparty["country"] == "United Kingdom"
        assert counterparty["registration_number"] == "Not recorded"
        assert counterparty["risk_tier"] == "unknown"
        assert counterparty["assigned_reviewer"] == "Unassigned"
        assert counterparty["submitted_at"] == counterparty["updated_at"]
        assert counterparty["decided_at"] == counterparty["updated_at"]

        claim = conn.execute(
            "SELECT * FROM claims WHERE id='CLM-LEGACY'"
        ).fetchone()
        assert claim["claim_type"] == "unknown"
        assert claim["status"] == "approved"
        assert claim["submitted_at"] == claim["updated_at"]
        assert claim["decided_at"] == claim["updated_at"]

        evidence = conn.execute(
            "SELECT * FROM counterparty_evidence WHERE id='EV-LEGACY'"
        ).fetchone()
        assert evidence["source"] == "Kestrel Ratings"
        assert evidence["value"] == "A-, stable outlook"

        flag = conn.execute(
            "SELECT * FROM flags WHERE key='sandbox.old_flag'"
        ).fetchone()
        assert flag["environment"] == "staging"
        assert flag["owner_team"] == "Unassigned"
        assert conn.execute(
            "SELECT details FROM audit_events WHERE resource_id='CP-LEGACY'"
        ).fetchone()["details"] is None
        audit = conn.execute(
            """SELECT actor_username, reason FROM audit_events
               WHERE resource_id='CP-LEGACY'"""
        ).fetchone()
        assert audit["actor_username"] == "rita.reviewer"
        assert audit["reason"] == "Legacy audit record"

        imported_counterparty = conn.execute(
            "SELECT id FROM counterparties WHERE id='CP-IMPORTED'"
        ).fetchone()
        assert imported_counterparty["id"] == "CP-IMPORTED"

        columns = {
            table: {
                row["name"]
                for row in conn.execute(f"PRAGMA table_info({table})")
            }
            for table in (
                "counterparties",
                "counterparty_evidence",
                "audit_events",
            )
        }
        assert "market" not in columns["counterparties"]
        assert not {
            "source_type",
            "rated_entity_or_market",
            "provenance",
        } & columns["counterparty_evidence"]
        assert "actor_user_id" not in columns["audit_events"]

        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert {"entitlements", "control_events"} <= tables
        assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0] == 2
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        conn.close()

    assert reset_db(db_path) is True
    conn = sqlite3.connect(db_path)
    try:
        assert conn.execute("SELECT COUNT(*) FROM counterparties").fetchone()[0] == 12
        assert conn.execute("SELECT COUNT(*) FROM counterparty_evidence").fetchone()[0] == 24
        assert conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0] == 25
    finally:
        conn.close()


def test_unmigratable_schema_has_reseed_instructions(tmp_path):
    db_path = tmp_path / "incompatible.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("CREATE TABLE counterparties (id TEXT PRIMARY KEY)")
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(RuntimeError, match=r"delete data/portal\.db and reseed"):
        init_db(db_path)
