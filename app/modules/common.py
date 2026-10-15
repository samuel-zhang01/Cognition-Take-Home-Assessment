from datetime import date, datetime, timezone
from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.core.auth import find_session_user, COOKIE_NAME
from app.core.registry import MODULES, NAV_GROUPS


templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parents[1] / "templates")
)


def format_datetime(value):
    if not value:
        return ""
    try:
        if len(value) == 10:
            return date.fromisoformat(value).strftime("%d %b %Y")
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    except (TypeError, ValueError):
        return value


templates.env.filters["datetime"] = format_datetime


def page_user(request, conn):
    return find_session_user(conn, request.cookies.get(COOKIE_NAME))


def render(request, template_name, **context):
    context.setdefault("modules", MODULES)
    context.setdefault("nav_groups", NAV_GROUPS)
    return templates.TemplateResponse(
        request=request, name=template_name, context={"request": request, **context}
    )
