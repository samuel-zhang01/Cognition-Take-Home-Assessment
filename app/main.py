import os
from pathlib import Path

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.core.auth import (
    COOKIE_NAME,
    current_user,
    find_session_user,
    get_connection,
    public_identity,
    verify_password,
)
from app.core.commands import CommandError
from app.core.db import init_db
from app.core.registry import MODULES
from app.modules import audit_view, claims, counterparties, flags
from app.modules.common import render
from app.seed import seed_if_empty


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
        return render(request, "home.html", user=user, modules=MODULES)

    @application.get("/login", response_class=HTMLResponse)
    def login_page(request: Request):
        return render(request, "login.html", error=None, user=None, modules=MODULES)

    @application.post("/login", response_class=HTMLResponse)
    def login(
        request: Request,
        username: str = Form(...),
        password: str = Form(...),
        conn=Depends(get_connection),
    ):
        row = conn.execute(
            """SELECT id, username, display_name, role, password_salt, password_hash
               FROM users WHERE username = ?""",
            (username,),
        ).fetchone()
        if row is None or not verify_password(
            password, row["password_salt"], row["password_hash"]
        ):
            return render(
                request,
                "login.html",
                error="Invalid username or password",
                user=None,
                modules=MODULES,
            )
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
        )
        return response

    @application.post("/logout")
    def logout(request: Request, conn=Depends(get_connection)):
        token = request.cookies.get(COOKIE_NAME)
        if token:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
        response = RedirectResponse("/login", status_code=303)
        response.delete_cookie(COOKIE_NAME)
        return response

    return application


app = create_app()
