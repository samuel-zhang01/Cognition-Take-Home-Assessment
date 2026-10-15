import csv
import io

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.status import HTTP_413_REQUEST_ENTITY_TOO_LARGE

from app.core.auth import current_user, get_connection
from app.core.audit import list_audit, write_audit
from app.core.controls import record_control_event
from app.core.dataio import IMPORT_SPECS, validate_rows
from app.core.db import transaction
from app.core.permissions import AUDIT_SCOPE, ROLE_PERMISSIONS
from app.modules.common import page_user, render


router = APIRouter()
MAX_FILE_BYTES = 1_000_000
MAX_ROWS = 1000
EXPORT_COLUMNS = {
    "counterparties": (
        "id", "name", "kind", "country", "registration_number", "risk_tier",
        "assigned_reviewer", "status", "submitted_at", "decided_at", "version",
    ),
    "claims": (
        "id", "counterparty_id", "claimant_ref", "claim_type", "description",
        "amount_minor", "currency", "status", "submitted_at", "decided_at", "version",
    ),
    "flags": ("key", "description", "enabled", "environment", "owner_team", "version", "updated_at"),
    "access_reviews": (
        "id", "employee", "team", "system", "access_level", "last_used_at",
        "quarter", "status", "decided_at", "version",
    ),
}


def _upload_result(rows, errors, committed=False):
    if any(error["row"] == 1 for error in errors):
        valid = 0
    else:
        invalid_rows = {error["row"] for error in errors if error["row"] > 1}
        valid = max(0, rows - len(invalid_rows))
    return {
        "rows": rows,
        "valid": valid,
        "errors": errors,
        "committed": committed,
    }


def _parse_upload(contents, spec, conn):
    try:
        text = contents.decode("utf-8-sig")
    except UnicodeDecodeError:
        return [], [{"row": 1, "column": "file", "message": "Upload a UTF-8 CSV file."}], 0
    try:
        reader = csv.DictReader(io.StringIO(text, newline=""))
        parsed, errors = validate_rows(conn, spec, reader)
    except csv.Error:
        return [], [{"row": 1, "column": "file", "message": "The CSV file could not be read."}], 0
    return parsed, errors, len(parsed)


@router.post("/api/import/{module}")
async def import_csv(
    module: str,
    file: UploadFile = File(...),
    reason: str = Form(""),
    dry_run: bool = Form(True),
    conn=Depends(get_connection),
    user=Depends(current_user),
):
    spec = IMPORT_SPECS.get(module)
    if spec is None:
        return JSONResponse(status_code=404, content={"detail": "Import module not found"})
    if spec.permission not in ROLE_PERMISSIONS.get(user["role"], set()):
        record_control_event(conn, user, module, "", "forbidden")
        return JSONResponse(status_code=403, content={"error": "forbidden", "detail": "Permission denied"})
    reason = reason.strip()
    if len(reason) < 3 or len(reason) > 500:
        errors = [{"row": 0, "column": "reason", "message": "Reason must contain 3 to 500 characters."}]
        if not dry_run:
            record_control_event(conn, user, module, "", "validation_failed")
        return JSONResponse(status_code=422, content=_upload_result(0, errors))
    contents = await file.read(MAX_FILE_BYTES + 1)
    if len(contents) > MAX_FILE_BYTES:
        if not dry_run:
            record_control_event(conn, user, module, "", "validation_failed")
        return JSONResponse(
            status_code=HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={
                "rows": 0,
                "valid": 0,
                "errors": [{"row": 0, "column": "file", "message": "CSV files must be 1 MB or smaller."}],
                "committed": False,
            },
        )
    parsed, errors, row_count = _parse_upload(contents, spec, conn)
    if row_count > MAX_ROWS:
        if not dry_run:
            record_control_event(conn, user, module, "", "validation_failed")
        return JSONResponse(
            status_code=HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={
                "rows": row_count,
                "valid": 0,
                "errors": [{"row": 0, "column": "file", "message": "CSV files must contain 1,000 rows or fewer."}],
                "committed": False,
            },
        )
    if errors:
        if not dry_run:
            record_control_event(conn, user, module, "", "validation_failed")
        return _upload_result(row_count, errors)
    if dry_run:
        return _upload_result(row_count, [], committed=False)

    commit_errors = []
    with transaction(conn):
        parsed_again, commit_errors, commit_rows = _parse_upload(contents, spec, conn)
        if not commit_errors and commit_rows == row_count:
            for row in parsed_again:
                spec.insert(conn, row)
            write_audit(
                conn,
                actor_username=user["username"],
                actor_role=user["role"],
                module=module,
                resource_type="dataset",
                resource_id=module,
                action="import",
                reason=reason,
                before={},
                after={"rows": row_count},
                resource_version=1,
                details={"rows": row_count, "filename": file.filename or "upload.csv"},
            )
    if commit_errors:
        record_control_event(conn, user, module, "", "validation_failed")
        return _upload_result(row_count, commit_errors)
    return _upload_result(row_count, [], committed=True)


@router.get("/api/import/{module}/template.csv")
def import_template(
    module: str,
    conn=Depends(get_connection),
    user=Depends(current_user),
):
    spec = IMPORT_SPECS.get(module)
    if spec is None:
        return JSONResponse(status_code=404, content={"detail": "Import module not found"})
    if spec.permission not in ROLE_PERMISSIONS.get(user["role"], set()):
        return JSONResponse(status_code=403, content={"error": "forbidden", "detail": "Permission denied"})
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow([column.name for column in spec.columns])
    writer.writerow(
        {
            "counterparties": (
                "CP-ONB-001", "Linden Harbour Assurance", "insurer", "United Kingdom",
                "UK-FCA-883104", "low", "rita.reviewer", "2026-10-15",
            ),
            "claims": (
                "CLM-ONB-001", "CP-001", "CUST-8401", "travel disruption",
                "Overnight stay after a cancelled flight", "185.00", "GBP", "2026-10-15",
            ),
            "access_reviews": (
                "ENT-ONB-001", "Morgan Ellis", "Finance", "Stripe Dashboard",
                "Refunds analyst", "2026-10-14", "2026-Q4",
            ),
        }[module]
    )
    return Response(
        output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{module}_template.csv"'},
    )


def _export_rows(conn, module, user):
    if module == "audit":
        return list_audit(conn, user)
    return [
        dict(row)
        for row in conn.execute(f"SELECT {', '.join(EXPORT_COLUMNS[module])} FROM {module if module != 'access_reviews' else 'entitlements'} ORDER BY 1").fetchall()
    ]


def _write_export_audit(conn, user, module, row_count, file_format):
    with transaction(conn):
        write_audit(
            conn,
            actor_username=user["username"],
            actor_role=user["role"],
            module=module,
            resource_type="dataset",
            resource_id=module,
            action="export",
            reason="Data export",
            before={},
            after={"rows": row_count, "format": file_format},
            resource_version=1,
            details={"rows": row_count, "format": file_format},
        )


def _csv_response(rows, columns, filename):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return Response(
        output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/api/export/{module}.csv")
def export_dataset(
    module: str,
    conn=Depends(get_connection),
    user=Depends(current_user),
):
    if "modules.read" not in ROLE_PERMISSIONS.get(user["role"], set()):
        return JSONResponse(status_code=403, content={"error": "forbidden", "detail": "Permission denied"})
    if module == "audit":
        rows = _export_rows(conn, "audit", user)
        _write_export_audit(conn, user, "audit", len(rows), "csv")
        return _csv_response(
            rows,
            (
                "id", "at", "actor_username", "actor_role", "module",
                "resource_type", "resource_id", "action", "reason", "before_json",
                "after_json", "resource_version", "details",
            ),
            "audit.csv",
        )
    if module not in EXPORT_COLUMNS:
        return JSONResponse(status_code=404, content={"detail": "Export module not found"})
    rows = _export_rows(conn, module, user)
    _write_export_audit(conn, user, module, len(rows), "csv")
    columns = EXPORT_COLUMNS[module]
    if module == "access_reviews":
        columns = tuple("id" if column == "id" else column for column in columns)
    return _csv_response(rows, columns, f"{module}.csv")


@router.get("/api/export/audit.json")
def export_audit_json(conn=Depends(get_connection), user=Depends(current_user)):
    rows = _export_rows(conn, "audit", user)
    _write_export_audit(conn, user, "audit", len(rows), "json")
    return JSONResponse(
        rows,
        headers={"Content-Disposition": 'attachment; filename="audit.json"'},
    )


@router.get("/data", response_class=HTMLResponse)
def data_page(request: Request, conn=Depends(get_connection)):
    user = page_user(request, conn)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    available = [
        spec for spec in IMPORT_SPECS.values()
        if spec.permission in ROLE_PERMISSIONS.get(user["role"], set())
    ]
    return render(
        request,
        "data.html",
        user=user,
        permissions=ROLE_PERMISSIONS[user["role"]],
        import_specs=available,
        export_modules=tuple(EXPORT_COLUMNS),
        is_auditor=user["role"] == "auditor",
        audit_scope=sorted(AUDIT_SCOPE.get(user["role"], set())),
    )
