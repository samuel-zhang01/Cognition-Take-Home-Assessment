from typing import Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict

from app.core.auth import get_connection, require_permission, utc_now
from app.core.audit import list_audit
from app.core.commands import InvalidTransition, run_command
from app.core.permissions import ROLE_PERMISSIONS
from app.modules.common import page_user, render


router = APIRouter()


class DecisionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    decision: Literal["certify", "revoke"]
    reason: str | None = None
    expected_version: int


def list_entitlements(conn, status=None, resource_id=None):
    conditions = []
    args = []
    if status:
        conditions.append("status = ?")
        args.append(status)
    if resource_id:
        conditions.append("id = ?")
        args.append(resource_id)
    query = "SELECT * FROM entitlements"
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY id"
    return [dict(row) for row in conn.execute(query, args).fetchall()]


@router.get("/api/access-reviews")
def api_access_reviews(
    status: str | None = None,
    conn=Depends(get_connection),
    user=Depends(require_permission("modules.read")),
):
    return list_entitlements(conn, status)


@router.post("/api/access-reviews/{entitlement_id}/decide")
def decide_access(
    entitlement_id: str,
    body: DecisionRequest,
    conn=Depends(get_connection),
    user=Depends(require_permission("access_reviews.decide")),
):
    def apply(row):
        if row["status"] == "revoked" or (
            row["status"] == "certified" and body.decision == "certify"
        ):
            raise InvalidTransition("This access review has already been decided")
        return {
            "status": "certified" if body.decision == "certify" else "revoked",
            "decided_at": utc_now(),
        }

    return run_command(
        conn,
        user,
        permission="access_reviews.decide",
        module="access_reviews",
        table="entitlements",
        resource_type="entitlement",
        resource_id=entitlement_id,
        id_column="id",
        action=body.decision,
        reason=body.reason,
        expected_version=body.expected_version,
        apply=apply,
    )


@router.get("/access-reviews")
def access_reviews_page(
    request: Request,
    status: str | None = None,
    resource_id: str | None = None,
    conn=Depends(get_connection),
):
    user = page_user(request, conn)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    return render(
        request,
        "access_reviews.html",
        user=user,
        permissions=ROLE_PERMISSIONS[user["role"]],
        entitlements=list_entitlements(conn, status, resource_id),
        audit=list_audit(conn, user, module="access_reviews")[:8],
        selected_status=status or "",
    )


@router.get("/access-reviews/{entitlement_id}")
def access_review_detail(
    entitlement_id: str,
    request: Request,
    conn=Depends(get_connection),
):
    user = page_user(request, conn)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    entitlement = conn.execute(
        "SELECT * FROM entitlements WHERE id = ?", (entitlement_id,)
    ).fetchone()
    if entitlement is None:
        return RedirectResponse("/access-reviews", status_code=303)
    return render(
        request,
        "access_review_detail.html",
        user=user,
        permissions=ROLE_PERMISSIONS[user["role"]],
        entitlement=dict(entitlement),
        audit=list_audit(
            conn, user, module="access_reviews", resource_id=entitlement_id
        ),
    )
