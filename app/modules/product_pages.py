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
        return {"rounds": [], "access_reviews_build": {}, "tests_passing": 0}
    return json.loads(path.read_text())


def source_lines(files):
    count = 0
    for source in files:
        path = REPO_ROOT / source
        if path.exists():
            count += len(path.read_text(encoding="utf-8").splitlines())
    return count


def _delivery_summary(log):
    rounds = log.get("rounds", [])
    return {
        "rounds": len(rounds),
        "total_wall_clock_minutes": round(
            sum(item["wall_clock_minutes"] for item in rounds)
        ),
        "tests_passing": log.get("tests_passing", 0),
    }


@router.get("/business-case", response_class=HTMLResponse)
def business_case(request: Request, conn=Depends(get_connection)):
    user = page_user(request, conn)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    log = load_delivery_log()
    rounds = log.get("rounds", [])
    return render(
        request,
        "business_case.html",
        user=user,
        measured_minutes=round(rounds[1]["wall_clock_minutes"]) if len(rounds) > 1 else 22,
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
        rounds=log.get("rounds", []),
        summary=_delivery_summary(log),
    )


@router.get("/apps", response_class=HTMLResponse)
def apps_page(request: Request, conn=Depends(get_connection)):
    user = page_user(request, conn)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    log = load_delivery_log()
    access_build = log.get("access_reviews_build", {})
    rounds = log.get("rounds", [])
    first_round_minutes = round(rounds[0]["wall_clock_minutes"]) if rounds else 11
    second_round_minutes = round(rounds[1]["wall_clock_minutes"]) if len(rounds) > 1 else 22
    apps = []
    for module in MODULES:
        apps.append(
            {
                "spec": module,
                "loc": source_lines(module.source_files),
                "round_number": 2 if module.key == "access_reviews" else 1,
            }
        )
    return render(
        request,
        "apps.html",
        user=user,
        apps=apps,
        access_build=access_build,
        first_round_minutes=first_round_minutes,
        second_round_minutes=second_round_minutes,
    )
