from datetime import datetime, timezone
from typing import Callable

from app.core.audit import write_audit
from app.core.db import transaction
from app.core.permissions import ROLE_PERMISSIONS


class CommandError(Exception):
    status_code = 400
    code = "command_error"

    def __init__(self, detail, **extra):
        super().__init__(detail)
        self.detail = detail
        self.extra = extra


class Forbidden(CommandError):
    status_code = 403
    code = "forbidden"


class ValidationFailed(CommandError):
    status_code = 422
    code = "validation_failed"


class NotFound(CommandError):
    status_code = 404
    code = "not_found"


class StaleVersion(CommandError):
    status_code = 409
    code = "stale_version"


class InvalidTransition(CommandError):
    status_code = 409
    code = "invalid_transition"


def run_command(
    conn,
    user,
    *,
    permission: str,
    module: str,
    table: str,
    resource_type: str,
    resource_id: str,
    id_column: str,
    action: str,
    reason: str | None,
    expected_version: int,
    apply: Callable[[dict], dict],
) -> dict:
    if permission not in ROLE_PERMISSIONS.get(user["role"], set()):
        raise Forbidden("Permission denied")
    reason = (reason or "").strip()
    if len(reason) < 3 or len(reason) > 500:
        raise ValidationFailed("Reason must contain 3 to 500 characters")

    with transaction(conn):
        row = conn.execute(
            f"SELECT * FROM {table} WHERE {id_column} = ?", (resource_id,)
        ).fetchone()
        if row is None:
            raise NotFound(f"{resource_type} not found")
        current = dict(row)
        if current["version"] != expected_version:
            raise StaleVersion(
                "Resource has changed; reload and try again",
                current_version=current["version"],
            )
        changes = apply(current)
        if not changes:
            raise InvalidTransition("The requested change does not alter this resource")
        before = {key: current[key] for key in changes}
        after = dict(changes)
        now = datetime.now(timezone.utc).isoformat()
        assignments = [f"{key} = ?" for key in changes]
        values = list(changes.values())
        assignments.extend(("version = version + 1", "updated_at = ?"))
        values.extend((now, resource_id, expected_version))
        cursor = conn.execute(
            f"UPDATE {table} SET {', '.join(assignments)} "
            f"WHERE {id_column} = ? AND version = ?",
            values,
        )
        if cursor.rowcount != 1:
            latest = conn.execute(
                f"SELECT version FROM {table} WHERE {id_column} = ?", (resource_id,)
            ).fetchone()
            raise StaleVersion(
                "Resource has changed; reload and try again",
                current_version=latest["version"] if latest else None,
            )
        updated = dict(
            conn.execute(
                f"SELECT * FROM {table} WHERE {id_column} = ?", (resource_id,)
            ).fetchone()
        )
        write_audit(
            conn,
            actor_user_id=user["id"],
            actor_role=user["role"],
            module=module,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            reason=reason,
            before=before,
            after=after,
            resource_version=updated["version"],
        )
    return updated
