from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict
from typing import Literal

from app.core.auth import get_connection
from app.core.audit import list_audit
from app.core.commands import InvalidTransition, run_command
from app.core.permissions import ROLE_PERMISSIONS
from app.core.auth import require_permission
from app.modules.common import page_user, render


router = APIRouter()


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    decision: Literal["approve", "reject"]
    reason: str | None = None
    expected_version: int


def list_counterparties(conn):
    return [
        dict(row)
        for row in conn.execute(
            """SELECT c.*, COUNT(cl.id) AS linked_claims
               FROM counterparties c LEFT JOIN claims cl ON cl.counterparty_id = c.id
               GROUP BY c.id ORDER BY c.id"""
        ).fetchall()
    ]


def get_counterparty(conn, counterparty_id):
    row = conn.execute(
        "SELECT * FROM counterparties WHERE id = ?", (counterparty_id,)
    ).fetchone()
    if not row:
        return None
    data = dict(row)
    data["evidence"] = [
        dict(item)
        for item in conn.execute(
            """SELECT * FROM counterparty_evidence
               WHERE counterparty_id = ? ORDER BY evidence_type, id""",
            (counterparty_id,),
        ).fetchall()
    ]
    data["claims"] = [
        dict(item)
        for item in conn.execute(
            "SELECT * FROM claims WHERE counterparty_id = ? ORDER BY id",
            (counterparty_id,),
        ).fetchall()
    ]
    return data


@router.get("/api/counterparties")
def api_counterparties(
    conn=Depends(get_connection),
    user=Depends(require_permission("counterparty.read")),
):
    return list_counterparties(conn)


@router.get("/api/counterparties/{counterparty_id}")
def api_counterparty(
    counterparty_id: str,
    conn=Depends(get_connection),
    user=Depends(require_permission("counterparty.read")),
):
    data = get_counterparty(conn, counterparty_id)
    if data is None:
        from app.core.commands import NotFound

        raise NotFound("Counterparty not found")
    return data


@router.post("/api/counterparties/{counterparty_id}/review")
def review_counterparty(
    counterparty_id: str,
    body: ReviewRequest,
    conn=Depends(get_connection),
    user=Depends(require_permission("counterparty.review")),
):
    def apply(row):
        if row["status"] != "pending_review":
            raise InvalidTransition("Only pending counterparties can be reviewed")
        return {"status": "approved" if body.decision == "approve" else "rejected"}

    return run_command(
        conn,
        user,
        permission="counterparty.review",
        module="counterparties",
        table="counterparties",
        resource_type="counterparty",
        resource_id=counterparty_id,
        id_column="id",
        action=f"review_{body.decision}",
        reason=body.reason,
        expected_version=body.expected_version,
        apply=apply,
    )


@router.get("/counterparties")
def counterparties_page(request: Request, conn=Depends(get_connection)):
    user = page_user(request, conn)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    return render(
        request,
        "counterparties.html",
        user=user,
        permissions=ROLE_PERMISSIONS[user["role"]],
        counterparties=list_counterparties(conn),
    )


@router.get("/counterparties/{counterparty_id}")
def counterparty_page(
    counterparty_id: str, request: Request, conn=Depends(get_connection)
):
    user = page_user(request, conn)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    counterparty = get_counterparty(conn, counterparty_id)
    if counterparty is None:
        return render(request, "not_found.html", user=user, message="Counterparty not found")
    return render(
        request,
        "counterparty_detail.html",
        user=user,
        permissions=ROLE_PERMISSIONS[user["role"]],
        counterparty=counterparty,
        audit=list_audit(conn, user, module="counterparties", resource_id=counterparty_id),
    )
