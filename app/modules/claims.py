from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict

from app.core.auth import get_connection, require_permission
from app.core.audit import list_audit
from app.core.commands import InvalidTransition, NotFound, run_command
from app.core.permissions import ROLE_PERMISSIONS
from app.modules.common import page_user, render


router = APIRouter()


class ApproveRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    reason: str | None = None
    expected_version: int


def list_claims(conn):
    return [
        dict(row)
        for row in conn.execute(
            """SELECT cl.*, cp.name AS counterparty_name, cp.status AS counterparty_status
               FROM claims cl JOIN counterparties cp ON cp.id = cl.counterparty_id
               ORDER BY cl.id"""
        ).fetchall()
    ]


def get_claim(conn, claim_id):
    row = conn.execute(
        """SELECT cl.*, cp.name AS counterparty_name, cp.status AS counterparty_status
           FROM claims cl JOIN counterparties cp ON cp.id = cl.counterparty_id
           WHERE cl.id = ?""",
        (claim_id,),
    ).fetchone()
    return dict(row) if row else None


@router.get("/api/claims")
def api_claims(
    conn=Depends(get_connection), user=Depends(require_permission("claim.read"))
):
    return list_claims(conn)


@router.get("/api/claims/{claim_id}")
def api_claim(
    claim_id: str,
    conn=Depends(get_connection),
    user=Depends(require_permission("claim.read")),
):
    claim = get_claim(conn, claim_id)
    if claim is None:
        raise NotFound("Claim not found")
    return claim


@router.post("/api/claims/{claim_id}/approve")
def approve_claim(
    claim_id: str,
    body: ApproveRequest,
    conn=Depends(get_connection),
    user=Depends(require_permission("claim.approve")),
):
    def apply(row):
        if row["status"] != "submitted":
            raise InvalidTransition("Only submitted claims can be approved")
        return {"status": "approved_simulated"}

    return run_command(
        conn,
        user,
        permission="claim.approve",
        module="claims",
        table="claims",
        resource_type="claim",
        resource_id=claim_id,
        id_column="id",
        action="approve_simulated",
        reason=body.reason,
        expected_version=body.expected_version,
        apply=apply,
    )


@router.get("/claims")
def claims_page(request: Request, conn=Depends(get_connection)):
    user = page_user(request, conn)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    return render(
        request,
        "claims.html",
        user=user,
        permissions=ROLE_PERMISSIONS[user["role"]],
        claims=list_claims(conn),
    )


@router.get("/claims/{claim_id}")
def claim_page(claim_id: str, request: Request, conn=Depends(get_connection)):
    user = page_user(request, conn)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    claim = get_claim(conn, claim_id)
    if claim is None:
        return render(request, "not_found.html", user=user, message="Claim not found")
    return render(
        request,
        "claim_detail.html",
        user=user,
        permissions=ROLE_PERMISSIONS[user["role"]],
        claim=claim,
        audit=list_audit(conn, user, module="claims", resource_id=claim_id),
    )
