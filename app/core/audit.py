import json

from app.core.auth import utc_now
from app.core.permissions import AUDIT_SCOPE


def write_audit(
    conn,
    *,
    actor_username,
    actor_role,
    module,
    resource_type,
    resource_id,
    action,
    reason,
    before,
    after,
    resource_version,
    details=None,
):
    conn.execute(
        """INSERT INTO audit_events
           (at, actor_username, actor_role, module, resource_type, resource_id,
            action, reason, before_json, after_json, resource_version, details)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            utc_now(),
            actor_username,
            actor_role,
            module,
            resource_type,
            resource_id,
            action,
            reason,
            json.dumps(before, sort_keys=True),
            json.dumps(after, sort_keys=True),
            resource_version,
            json.dumps(details, sort_keys=True) if details is not None else None,
        ),
    )


def list_audit(conn, user, module=None, resource_id=None):
    scope = AUDIT_SCOPE.get(user["role"], set())
    if module and module not in scope:
        return []
    allowed = sorted(scope)
    if not allowed:
        return []
    placeholders = ",".join("?" for _ in allowed)
    query = f"SELECT * FROM audit_events WHERE module IN ({placeholders})"
    args = list(allowed)
    if module:
        query += " AND module = ?"
        args.append(module)
    if resource_id:
        query += " AND resource_id = ?"
        args.append(resource_id)
    query += " ORDER BY id DESC"
    return [dict(row) for row in conn.execute(query, args).fetchall()]
