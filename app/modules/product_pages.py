import json
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.registry import MODULES
from app.core.auth import get_connection
from app.modules.common import page_user, render


router = APIRouter()
APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parent


def load_delivery_log():
    path = APP_ROOT / "delivery_log.json"
    if not path.exists():
        return {"entries": [], "tests_passing": 0}
    return json.loads(path.read_text())


def source_lines(files):
    count = 0
    for source in files:
        path = REPO_ROOT / source
        if path.exists():
            count += len(path.read_text(encoding="utf-8").splitlines())
    return count


def _delivery_summary(log):
    entries = log.get("entries", [])
    return {
        "accepted_changes": len(entries),
        "total_elapsed_min": sum(entry["elapsed_min"] for entry in entries),
        "tests_passing": log.get("tests_passing", 0),
    }


@router.get("/business-case", response_class=HTMLResponse)
def business_case(request: Request, conn=Depends(get_connection)):
    user = page_user(request, conn)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    log = load_delivery_log()
    return render(
        request,
        "business_case.html",
        user=user,
        measured_minutes=log.get("access_reviews_build", {}).get("elapsed_min", 1),
    )


@router.get("/delivery", response_class=HTMLResponse)
def delivery_page(request: Request, conn=Depends(get_connection)):
    user = page_user(request, conn)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    log = load_delivery_log()
    return render(
        request,
        "delivery.html",
        user=user,
        entries=log.get("entries", []),
        summary=_delivery_summary(log),
    )


@router.get("/apps", response_class=HTMLResponse)
def apps_page(request: Request, conn=Depends(get_connection)):
    user = page_user(request, conn)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    log = load_delivery_log()
    entries = log.get("entries", [])
    access_build = log.get("access_reviews_build", {})
    first_build = next((entry for entry in entries if entry["commit"].startswith("6ccf791")), None)
    apps = []
    for module in MODULES:
        if module.key == "access_reviews":
            build_minutes = access_build.get("elapsed_min", 1)
        else:
            build_minutes = first_build["elapsed_min"] if first_build else 0
        apps.append(
            {
                "spec": module,
                "loc": source_lines(module.source_files),
                "build_minutes": build_minutes,
            }
        )
    return render(
        request,
        "apps.html",
        user=user,
        apps=apps,
        access_build=access_build,
    )
