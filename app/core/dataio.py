import sqlite3
from dataclasses import dataclass
from decimal import Decimal, DecimalException, InvalidOperation
from typing import Callable, Literal


SQLITE_MAX_INTEGER = 2**63 - 1


@dataclass(frozen=True)
class Column:
    name: str
    kind: Literal["str", "int", "decimal", "date", "choice"]
    required: bool = True
    choices: tuple[str, ...] = ()


@dataclass(frozen=True)
class ImportSpec:
    module: str
    permission: str
    table: str
    key: str
    columns: tuple[Column, ...]
    insert: Callable[[sqlite3.Connection, dict], None]
    validate_row: Callable[[sqlite3.Connection, dict], list[str]] | None = None


def _insert_counterparty(conn, row):
    conn.execute(
        """INSERT INTO counterparties
           (id, name, kind, country, registration_number, risk_tier,
            assigned_reviewer, status, submitted_at, decided_at, version, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'pending_review', ?, NULL, 1, ?)""",
        (
            row["id"],
            row["name"],
            row["kind"],
            row["country"],
            row["registration_number"],
            row["risk_tier"],
            row["assigned_reviewer"],
            row["submitted_at"],
            row["submitted_at"],
        ),
    )


def _insert_claim(conn, row):
    amount_minor = int(row["amount"] * 100)
    conn.execute(
        """INSERT INTO claims
           (id, counterparty_id, claimant_ref, claim_type, description,
            amount_minor, currency, status, submitted_at, decided_at, version, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'submitted', ?, NULL, 1, ?)""",
        (
            row["id"],
            row["counterparty_id"],
            row["claimant_ref"],
            row["claim_type"],
            row["description"],
            amount_minor,
            row["currency"],
            row["submitted_at"],
            row["submitted_at"],
        ),
    )


def _validate_claim(conn, row):
    if not conn.execute(
        "SELECT 1 FROM counterparties WHERE id = ?", (row["counterparty_id"],)
    ).fetchone():
        return [f"counterparty_id: Unknown counterparty {row['counterparty_id']}"]
    return []


def _insert_entitlement(conn, row):
    conn.execute(
        """INSERT INTO entitlements
           (id, employee, team, system, access_level, last_used_at, quarter,
            status, decided_at, version, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', NULL, 1, ?)""",
        (
            row["id"],
            row["employee"],
            row["team"],
            row["system"],
            row["access_level"],
            row["last_used_at"],
            row["quarter"],
            row["last_used_at"],
        ),
    )


IMPORT_SPECS = {
    "counterparties": ImportSpec(
        module="counterparties",
        permission="counterparties.import",
        table="counterparties",
        key="id",
        columns=(
            Column("id", "str"),
            Column("name", "str"),
            Column(
                "kind",
                "choice",
                choices=("insurer", "reinsurer", "claims administrator", "MGA"),
            ),
            Column("country", "str"),
            Column("registration_number", "str"),
            Column("risk_tier", "choice", choices=("low", "medium", "high")),
            Column("assigned_reviewer", "str"),
            Column("submitted_at", "date"),
        ),
        insert=_insert_counterparty,
    ),
    "claims": ImportSpec(
        module="claims",
        permission="claims.import",
        table="claims",
        key="id",
        columns=(
            Column("id", "str"),
            Column("counterparty_id", "str"),
            Column("claimant_ref", "str"),
            Column("claim_type", "choice", choices=(
                "travel disruption",
                "device damage",
                "card fraud refund",
                "duplicate charge refund",
                "merchant dispute",
            )),
            Column("description", "str"),
            Column("amount", "decimal"),
            Column("currency", "choice", choices=("USD", "GBP", "EUR")),
            Column("submitted_at", "date"),
        ),
        insert=_insert_claim,
        validate_row=_validate_claim,
    ),
    "access_reviews": ImportSpec(
        module="access_reviews",
        permission="access_reviews.import",
        table="entitlements",
        key="id",
        columns=(
            Column("id", "str"),
            Column("employee", "str"),
            Column("team", "str"),
            Column("system", "str"),
            Column("access_level", "str"),
            Column("last_used_at", "date"),
            Column("quarter", "choice", choices=("2026-Q4",)),
        ),
        insert=_insert_entitlement,
    ),
}


def parse_value(column, value):
    value = (value or "").strip()
    if not value:
        if column.required:
            raise ValueError("This field is required.")
        return None
    if column.kind == "str":
        return value
    if column.kind == "int":
        try:
            return int(value)
        except ValueError as exc:
            raise ValueError("Enter a whole number.") from exc
    if column.kind == "decimal":
        try:
            number = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("Enter a valid amount.") from exc
        if not number.is_finite() or number < 0:
            raise ValueError("Enter a non-negative amount.")
        if number.as_tuple().exponent < -2:
            raise ValueError("Enter an amount with no more than 2 decimal places.")
        try:
            if abs(number) > Decimal(SQLITE_MAX_INTEGER) / 100:
                raise ValueError("The amount exceeds the supported range.")
        except DecimalException as exc:
            raise ValueError("The amount exceeds the supported range.") from exc
        return number
    if column.kind == "date":
        from datetime import date

        try:
            return date.fromisoformat(value).isoformat()
        except ValueError as exc:
            raise ValueError("Enter a date in YYYY-MM-DD format.") from exc
    if column.kind == "choice":
        if value not in column.choices:
            raise ValueError(f"Choose one of: {', '.join(column.choices)}.")
        return value
    raise ValueError("Unsupported field type.")


def validate_rows(conn, spec, reader):
    rows = []
    errors = []
    seen = set()
    fieldnames = reader.fieldnames or []
    seen_headers = set()
    reported_duplicates = set()
    duplicate_headers = []
    for fieldname in fieldnames:
        if fieldname in seen_headers and fieldname not in reported_duplicates:
            duplicate_headers.append(fieldname)
            reported_duplicates.add(fieldname)
        seen_headers.add(fieldname)
    if duplicate_headers:
        return [], [
            {
                "row": 1,
                "column": fieldname or "header",
                "message": "Duplicate column.",
            }
            for fieldname in duplicate_headers
        ]

    known_columns = {column.name for column in spec.columns}
    for fieldname in fieldnames:
        if fieldname not in known_columns:
            errors.append(
                {
                    "row": 1,
                    "column": fieldname or "header",
                    "message": "Unknown column.",
                }
            )
    for column in spec.columns:
        if column.required and column.name not in fieldnames:
            errors.append(
                {"row": 1, "column": column.name, "message": "Required column is missing."}
            )
    for row_number, raw in enumerate(reader, start=2):
        parsed = {}
        if None in raw:
            errors.append(
                {
                    "row": row_number,
                    "column": "row",
                    "message": "The row has more fields than the header.",
                }
            )
        for column in spec.columns:
            try:
                parsed[column.name] = parse_value(column, raw.get(column.name))
            except ValueError as exc:
                errors.append(
                    {"row": row_number, "column": column.name, "message": str(exc)}
                )
        key_value = parsed.get(spec.key)
        if key_value:
            if key_value in seen:
                errors.append(
                    {"row": row_number, "column": spec.key, "message": "Duplicate key in file."}
                )
            else:
                seen.add(key_value)
            if conn.execute(
                f"SELECT 1 FROM {spec.table} WHERE {spec.key} = ?", (key_value,)
            ).fetchone():
                errors.append(
                    {"row": row_number, "column": spec.key, "message": "Key already exists."}
                )
        if spec.validate_row and all(
            column.name in parsed for column in spec.columns
        ):
            for message in spec.validate_row(conn, parsed):
                column, separator, detail = message.partition(":")
                errors.append(
                    {
                        "row": row_number,
                        "column": column if separator else "row",
                        "message": detail.strip() if separator else message,
                    }
                )
        rows.append(parsed)
    return rows, errors
