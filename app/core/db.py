import re
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


def _quote_identifier(name):
    return '"' + name.replace('"', '""') + '"'


def _table_ddl(table, name):
    match = re.search(
        rf"CREATE TABLE IF NOT EXISTS {re.escape(table)} \((.*?)\);",
        SCHEMA,
        re.DOTALL,
    )
    if match is None:
        raise RuntimeError(f"No current schema definition for table {table!r}.")
    return f"CREATE TABLE {_quote_identifier(name)} ({match.group(1)});"


def _table_info(conn, table):
    quoted_table = _quote_identifier(table)
    return {
        row["name"]: row
        for row in conn.execute(f"PRAGMA table_info({quoted_table})")
    }


def _expected_table_info(conn, table):
    probe = f"__schema_probe_{table}"
    conn.execute(_table_ddl(table, probe))
    try:
        return _table_info(conn, probe)
    finally:
        conn.execute(f"DROP TABLE {_quote_identifier(probe)}")


def _table_needs_rebuild(existing, expected):
    if set(existing) != set(expected):
        return True
    return any(
        bool(existing[name]["notnull"]) != bool(expected[name]["notnull"])
        for name in expected
    )


def _missing_column_expression(table, name, info):
    definition = MISSING_COLUMNS.get(table, {}).get(name)
    if definition:
        match = re.search(r"\bDEFAULT\s+(.+)$", definition, re.IGNORECASE)
        if match:
            return match.group(1)

    if info["dflt_value"] is not None:
        return str(info["dflt_value"])
    if not info["notnull"] or (
        info["pk"] and str(info["type"]).upper() == "INTEGER"
    ):
        return "NULL"
    raise RuntimeError(
        f"Cannot migrate {table!r}: missing required column {name!r} "
        "has no migration default. Back up the database; to start fresh, "
        "delete data/portal.db and reseed."
    )


def _column_expression(table, name, existing, expected):
    if (
        table == "counterparties"
        and name == "country"
        and "market" in existing
    ):
        market = f'old.{_quote_identifier("market")}'
        mapped_market = (
            f"CASE UPPER({market}) "
            "WHEN 'UK' THEN 'United Kingdom' "
            "WHEN 'US' THEN 'United States' "
            "WHEN 'EU' THEN 'Unknown' "
            f"ELSE COALESCE(NULLIF({market}, ''), 'Unknown') END"
        )
        if name in existing:
            country = f'old.{_quote_identifier(name)}'
            return (
                f"CASE WHEN {country} IS NULL OR {country} IN ('', 'Unknown') "
                f"THEN {mapped_market} ELSE {country} END"
            )
        return mapped_market

    if (
        table == "audit_events"
        and name == "actor_username"
        and name not in existing
        and "actor_user_id" in existing
    ):
        actor_id = f'old.{_quote_identifier("actor_user_id")}'
        return (
            "COALESCE((SELECT username FROM users "
            f"WHERE id = {actor_id}), 'unknown')"
        )

    if name in existing:
        return f"old.{_quote_identifier(name)}"
    return _missing_column_expression(table, name, expected[name])


def _rebuild_table(conn, table, existing, expected):
    new_table = f"{table}__new"
    if conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (new_table,),
    ).fetchone():
        raise RuntimeError(
            f"Cannot migrate table {table!r}: temporary table {new_table!r} "
            "already exists. Back up the database; to start fresh, "
            "delete data/portal.db and reseed."
        )
    conn.execute(_table_ddl(table, new_table))
    target_columns = list(expected)
    expressions = [
        _column_expression(table, name, existing, expected)
        for name in target_columns
    ]
    quoted_columns = ", ".join(_quote_identifier(name) for name in target_columns)
    selected_columns = ", ".join(expressions)
    conn.execute(
        f"INSERT INTO {_quote_identifier(new_table)} ({quoted_columns}) "
        f"SELECT {selected_columns} FROM {_quote_identifier(table)} AS old"
    )
    conn.execute(f"DROP TABLE {_quote_identifier(table)}")
    conn.execute(
        f"ALTER TABLE {_quote_identifier(new_table)} "
        f"RENAME TO {_quote_identifier(table)}"
    )


def _migrate_schema(conn):
    for table in REQUIRED_COLUMNS:
        existing = _table_info(conn, table)
        expected = _expected_table_info(conn, table)
        if _table_needs_rebuild(existing, expected):
            _rebuild_table(conn, table, existing, expected)

    for statement in re.findall(
        r"CREATE INDEX IF NOT EXISTS\s+.*?;", SCHEMA, re.DOTALL
    ):
        conn.execute(statement)

    violations = conn.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        details = ", ".join(
            f"{row['table']} row {row['rowid']} references {row['parent']}"
            for row in violations
        )
        raise RuntimeError(
            f"Database migration found foreign-key violations: {details}. "
            "Back up the database; to start fresh, delete data/portal.db and reseed."
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
            conn.execute("PRAGMA foreign_keys = OFF")
            try:
                with transaction(conn):
                    _migrate_schema(conn)
            finally:
                conn.execute("PRAGMA foreign_keys = ON")
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
