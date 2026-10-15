import os
from pathlib import Path

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.core.auth import (
    COOKIE_NAME,
    DEMO_USERS,
    clear_login_failures,
    cookie_secure,
    current_user,
    find_session_user,
    get_connection,
    login_attempt_allowed,
    login_attempt_lock,
    public_identity,
    verify_password,
)
from app.core.audit import list_audit
from app.core.commands import CommandError
from app.core.db import init_db
from app.core.registry import CORE_MODULES, MODULES, NEW_MODULES
from app.modules import (
    access_reviews,
    audit_view,
    claims,
    counterparties,
    data_transfer,
    flags,
    metrics,
    product_pages,
)
from app.modules.common import render
from app.seed import seed_if_empty


def login_response(request, error=None, status_code=200):
    show_demo_accounts = os.environ.get("SHOW_DEMO_ACCOUNTS", "1").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    response = render(
        request,
        "login.html",
        error=error,
        user=None,
        modules=MODULES,
        demo_users=DEMO_USERS if show_demo_accounts else (),
        demo_password=os.environ.get("DEMO_PASSWORD", "demo"),
        show_demo_accounts=show_demo_accounts,
    )
    response.status_code = status_code
    return response


def create_app(db_path=None):
    selected_db = db_path or os.environ.get("PORTAL_DB", "data/portal.db")
    if str(selected_db) != ":memory:":
        Path(selected_db).parent.mkdir(parents=True, exist_ok=True)
    init_db(selected_db)
    seed_if_empty(selected_db)

    application = FastAPI(title="Shared Operations Portal")
    application.state.db_path = str(selected_db)
    application.mount(
        "/static",
        StaticFiles(directory=str(Path(__file__).resolve().parent / "static")),
        name="static",
    )
    application.include_router(counterparties.router)
    application.include_router(claims.router)
    application.include_router(flags.router)
    application.include_router(audit_view.router)
    application.include_router(access_reviews.router)
    application.include_router(data_transfer.router)
    application.include_router(metrics.router)
    application.include_router(product_pages.router)

    @application.exception_handler(CommandError)
    async def command_error_handler(request, exc):
        payload = {"error": exc.code, "detail": exc.detail}
        payload.update(exc.extra)
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=exc.status_code, content=payload)

    @application.get("/api/me")
    def api_me(user=Depends(current_user)):
        return public_identity(user)

    @application.get("/", response_class=HTMLResponse)
    def home(request: Request, conn=Depends(get_connection)):
        user = find_session_user(conn, request.cookies.get(COOKIE_NAME))
        if user is None:
            return RedirectResponse("/login", status_code=303)
        return render(
            request,
            "home.html",
            user=user,
            modules=MODULES,
            core_modules=CORE_MODULES,
            new_modules=NEW_MODULES,
            metrics=metrics.collect_metrics(conn),
            recent_activity=list_audit(conn, user)[:8],
        )

    @application.get("/login", response_class=HTMLResponse)
    def login_page(request: Request):
        return login_response(request)

    @application.post("/login", response_class=HTMLResponse)
    def login(
        request: Request,
        username: str = Form(...),
        password: str = Form(...),
        conn=Depends(get_connection),
    ):
        client_ip = request.client.host if request.client else ""
        with login_attempt_lock(username, client_ip):
            if not login_attempt_allowed(username, client_ip):
                return login_response(
                    request,
                    error="Too many sign-in attempts. Try again in 15 minutes.",
                    status_code=429,
                )
            row = conn.execute(
                """SELECT id, username, display_name, role, password_salt, password_hash
                   FROM users WHERE username = ?""",
                (username,),
            ).fetchone()
            if row is None or not verify_password(
                password, row["password_salt"], row["password_hash"]
            ):
                return login_response(request, error="Invalid username or password")
            clear_login_failures(username, client_ip)
        import secrets

        from app.core.auth import utc_now

        token = secrets.token_urlsafe(32)
        conn.execute(
            "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
            (token, row["id"], utc_now()),
        )
        conn.commit()
        response = RedirectResponse("/", status_code=303)
        response.set_cookie(
            COOKIE_NAME,
            token,
            httponly=True,
            samesite="lax",
            secure=cookie_secure(request),
        )
        return response

    @application.post("/logout")
    def logout(request: Request, conn=Depends(get_connection)):
        token = request.cookies.get(COOKIE_NAME)
        if token:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
        response = RedirectResponse("/login", status_code=303)
        response.delete_cookie(
            COOKIE_NAME,
            httponly=True,
            samesite="lax",
            secure=cookie_secure(request),
        )
        return response

    return application


app = create_app()
