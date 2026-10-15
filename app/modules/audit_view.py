from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app.core.auth import get_connection, require_permission
from app.core.audit import list_audit
from app.modules.common import page_user, render


router = APIRouter()


@router.get("/api/audit")
def api_audit(
    module: str | None = None,
    resource_id: str | None = None,
    conn=Depends(get_connection),
    user=Depends(require_permission("modules.read")),
):
    return list_audit(conn, user, module=module, resource_id=resource_id)


@router.get("/audit")
def audit_page(
    request: Request,
    module: str | None = None,
    resource_id: str | None = None,
    conn=Depends(get_connection),
):
    user = page_user(request, conn)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    return render(
        request,
        "audit.html",
        user=user,
        events=list_audit(conn, user, module=module, resource_id=resource_id),
        selected_module=module or "",
        resource_id=resource_id or "",
    )
