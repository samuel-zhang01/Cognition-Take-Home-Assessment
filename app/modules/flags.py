from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict

from app.core.auth import get_connection, require_permission
from app.core.audit import list_audit
from app.core.commands import InvalidTransition, NotFound, run_command
from app.core.permissions import ROLE_PERMISSIONS
from app.modules.common import page_user, render


router = APIRouter()


class ChangeFlagRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool
    reason: str | None = None
    expected_version: int


def list_flags(conn, status=None):
    status_filter = " WHERE f.enabled = ?" if status in {"on", "off"} else ""
    args = (1 if status == "on" else 0,) if status_filter else ()
    return [
        {**dict(row), "enabled": bool(row["enabled"])}
        for row in conn.execute(
            """SELECT f.*, event.at AS last_changed_at,
                      event.actor_username AS last_changed_by,
                      event.reason AS last_change_reason
               FROM flags f
               LEFT JOIN audit_events event ON event.id = (
                   SELECT MAX(a.id) FROM audit_events a
                   WHERE a.module = 'flags' AND a.resource_id = f.key
               )
               {status_filter} ORDER BY f.key""",
            args,
        ).fetchall()
    ]


@router.get("/api/flags")
def api_flags(conn=Depends(get_connection), user=Depends(require_permission("flag.read"))):
    return list_flags(conn)


@router.post("/api/flags/{flag_key}/change")
def change_flag(
    flag_key: str,
    body: ChangeFlagRequest,
    conn=Depends(get_connection),
    user=Depends(require_permission("flag.change")),
):
    def apply(row):
        if bool(row["enabled"]) == body.enabled:
            raise InvalidTransition("Flag already has the requested value")
        return {"enabled": int(body.enabled)}

    return run_command(
        conn,
        user,
        permission="flag.change",
        module="flags",
        table="flags",
        resource_type="flag",
        resource_id=flag_key,
        id_column="key",
        action="change_enabled",
        reason=body.reason,
        expected_version=body.expected_version,
        apply=apply,
    )


@router.get("/flags")
def flags_page(
    request: Request, status: str | None = None, conn=Depends(get_connection)
):
    user = page_user(request, conn)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    return render(
        request,
        "flags.html",
        user=user,
        permissions=ROLE_PERMISSIONS[user["role"]],
        flags=list_flags(conn, status),
        selected_status=status or "",
    )
