import os
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.core.auth import hash_password
from app.core.db import init_db
from app.main import create_app


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
                actor_username TEXT NOT NULL,
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
        conn.execute(
            """INSERT INTO audit_events
               (at, actor_username, actor_role, module, resource_type, resource_id,
                action, reason, before_json, after_json, resource_version)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                updated_at,
                "rita.reviewer",
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

        flag = conn.execute(
            "SELECT * FROM flags WHERE key='sandbox.old_flag'"
        ).fetchone()
        assert flag["environment"] == "staging"
        assert flag["owner_team"] == "Unassigned"
        assert conn.execute(
            "SELECT details FROM audit_events WHERE resource_id='CP-LEGACY'"
        ).fetchone()["details"] is None
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert {"entitlements", "control_events"} <= tables
        assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0] == 1
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
