from datetime import datetime, timezone

from app.core.db import transaction


def record_control_event(conn, user, module, resource_id, outcome):
    with transaction(conn):
        conn.execute(
            """INSERT INTO control_events
               (at, actor_username, actor_role, module, resource_id, outcome)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                datetime.now(timezone.utc).isoformat(),
                user["username"],
                user["role"],
                module,
                str(resource_id or ""),
                outcome,
            ),
        )
