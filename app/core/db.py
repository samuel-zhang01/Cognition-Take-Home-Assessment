import sqlite3
from contextlib import contextmanager
from pathlib import Path


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL,
    password_salt TEXT NOT NULL,
    password_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS counterparties (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    country TEXT NOT NULL,
    registration_number TEXT NOT NULL,
    risk_tier TEXT NOT NULL,
    assigned_reviewer TEXT NOT NULL,
    status TEXT NOT NULL,
    submitted_at TEXT NOT NULL,
    decided_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS counterparty_evidence (
    id TEXT PRIMARY KEY,
    counterparty_id TEXT NOT NULL REFERENCES counterparties(id) ON DELETE CASCADE,
    evidence_type TEXT NOT NULL,
    source TEXT NOT NULL,
    value TEXT NOT NULL,
    as_of TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS claims (
    id TEXT PRIMARY KEY,
    counterparty_id TEXT NOT NULL REFERENCES counterparties(id),
    claimant_ref TEXT NOT NULL,
    claim_type TEXT NOT NULL,
    description TEXT NOT NULL,
    amount_minor INTEGER NOT NULL,
    currency TEXT NOT NULL,
    status TEXT NOT NULL,
    submitted_at TEXT NOT NULL,
    decided_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS flags (
    key TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    enabled INTEGER NOT NULL,
    environment TEXT NOT NULL,
    owner_team TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS entitlements (
    id TEXT PRIMARY KEY,
    employee TEXT NOT NULL,
    team TEXT NOT NULL,
    system TEXT NOT NULL,
    access_level TEXT NOT NULL,
    last_used_at TEXT NOT NULL,
    quarter TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'certified', 'revoked')),
    decided_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_events (
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
    resource_version INTEGER NOT NULL,
    details TEXT
);
CREATE TABLE IF NOT EXISTS control_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    actor_username TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    module TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (
        outcome IN ('forbidden', 'stale_version', 'invalid_transition', 'validation_failed')
    )
);
CREATE INDEX IF NOT EXISTS idx_audit_module_resource
    ON audit_events(module, resource_id, id);
CREATE INDEX IF NOT EXISTS idx_audit_module_at
    ON audit_events(module, at);
CREATE INDEX IF NOT EXISTS idx_control_events_at
    ON control_events(at);
"""

MISSING_COLUMNS = {
    "counterparties": {
        "country": "TEXT NOT NULL DEFAULT 'Unknown'",
        "registration_number": "TEXT NOT NULL DEFAULT 'Not recorded'",
        "risk_tier": "TEXT NOT NULL DEFAULT 'unknown'",
        "assigned_reviewer": "TEXT NOT NULL DEFAULT 'Unassigned'",
        "submitted_at": "TEXT NOT NULL DEFAULT ''",
        "decided_at": "TEXT",
    },
    "claims": {
        "claim_type": "TEXT NOT NULL DEFAULT 'unknown'",
        "submitted_at": "TEXT NOT NULL DEFAULT ''",
        "decided_at": "TEXT",
    },
    "flags": {
        "environment": "TEXT NOT NULL DEFAULT 'staging'",
        "owner_team": "TEXT NOT NULL DEFAULT 'Unassigned'",
    },
    "audit_events": {"details": "TEXT"},
}

REQUIRED_COLUMNS = {
    "users": {"id", "username", "display_name", "role", "password_salt", "password_hash"},
    "sessions": {"token", "user_id", "created_at"},
    "counterparties": {
        "id", "name", "kind", "country", "registration_number", "risk_tier",
        "assigned_reviewer", "status", "submitted_at", "decided_at", "version", "updated_at",
    },
    "counterparty_evidence": {
        "id", "counterparty_id", "evidence_type", "source", "value", "as_of",
    },
    "claims": {
        "id", "counterparty_id", "claimant_ref", "claim_type", "description",
        "amount_minor", "currency", "status", "submitted_at", "decided_at", "version",
        "updated_at",
    },
    "flags": {
        "key", "description", "enabled", "environment", "owner_team", "version", "updated_at",
    },
    "entitlements": {
        "id", "employee", "team", "system", "access_level", "last_used_at", "quarter",
        "status", "decided_at", "version", "updated_at",
    },
    "audit_events": {
        "id", "at", "actor_username", "actor_role", "module", "resource_type",
        "resource_id", "action", "reason", "before_json", "after_json", "resource_version",
        "details",
    },
    "control_events": {
        "id", "at", "actor_username", "actor_role", "module", "resource_id", "outcome",
    },
}


def _table_columns(conn, table):
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}


def _migrate_schema(conn):
    for table, additions in MISSING_COLUMNS.items():
        columns = _table_columns(conn, table)
        for name, definition in additions.items():
            if name not in columns:
                conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN {name} {definition}"
                )

    counterparty_columns = _table_columns(conn, "counterparties")
    if "market" in counterparty_columns:
        conn.execute(
            """UPDATE counterparties
               SET country = CASE UPPER(market)
                   WHEN 'UK' THEN 'United Kingdom'
                   WHEN 'US' THEN 'United States'
                   WHEN 'EU' THEN 'Unknown'
                   ELSE COALESCE(NULLIF(market, ''), 'Unknown')
               END
               WHERE country = 'Unknown'"""
        )
    conn.execute(
        """UPDATE counterparties SET submitted_at = updated_at
           WHERE submitted_at = ''"""
    )
    conn.execute(
        """UPDATE counterparties SET decided_at = updated_at
           WHERE decided_at IS NULL AND status NOT IN ('pending', 'pending_review')"""
    )
    conn.execute(
        """UPDATE claims SET submitted_at = updated_at
           WHERE submitted_at = ''"""
    )
    conn.execute(
        "UPDATE claims SET status = 'approved' WHERE status = 'approved_simulated'"
    )
    conn.execute(
        """UPDATE claims SET decided_at = updated_at
           WHERE decided_at IS NULL AND status IN ('approved', 'rejected')"""
    )

    for table, required in REQUIRED_COLUMNS.items():
        missing = required - _table_columns(conn, table)
        if missing:
            names = ", ".join(sorted(missing))
            raise RuntimeError(
                f"Existing table {table!r} is missing required columns: {names}. "
                "Back up the database; to start fresh, delete data/portal.db and reseed."
            )


def connect(db_path):
    path = str(db_path)
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=15, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 15000")
    return conn


def init_db(db_path):
    try:
        with connect(db_path) as conn:
            conn.executescript(SCHEMA)
            with transaction(conn):
                _migrate_schema(conn)
    except sqlite3.Error as exc:
        raise RuntimeError(
            "The existing portal database could not be migrated in place. "
            "Back up the database; to start fresh, delete data/portal.db and reseed."
        ) from exc


@contextmanager
def transaction(conn):
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
