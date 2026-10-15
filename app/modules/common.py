from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.core.auth import find_session_user, COOKIE_NAME
from app.core.registry import MODULES, NAV_GROUPS


templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parents[1] / "templates")
)


def page_user(request, conn):
    return find_session_user(conn, request.cookies.get(COOKIE_NAME))


def render(request, template_name, **context):
    context.setdefault("modules", MODULES)
    context.setdefault("nav_groups", NAV_GROUPS)
    return templates.TemplateResponse(
        request=request, name=template_name, context={"request": request, **context}
    )
