import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.core.auth import COOKIE_NAME, clear_login_failures
from app.core.db import init_db
from app.main import create_app
from app.seed import seed_if_empty


@pytest.fixture(autouse=True)
def clear_login_attempts():
    for username in ("rita.reviewer", "colin.claims", "fiona.flags", "aaron.auditor", "nina.access"):
        clear_login_failures(username, "testclient")
    yield
    for username in ("rita.reviewer", "colin.claims", "fiona.flags", "aaron.auditor", "nina.access"):
        clear_login_failures(username, "testclient")


def test_seed_if_empty_is_safe_for_repeated_and_concurrent_starts(tmp_path):
    db_path = tmp_path / "seed-race.db"
    init_db(db_path)

    with ThreadPoolExecutor(max_workers=2) as pool:
        seeded = list(pool.map(lambda _: seed_if_empty(db_path), range(2)))
    assert sorted(seeded) == [False, True]
    assert seed_if_empty(db_path) is False


def test_expired_session_is_rejected_and_deleted(tmp_path):
    db_path = tmp_path / "expired-session.db"
    application = create_app(db_path=db_path)
    with TestClient(application) as client:
        password = os.environ.get("DEMO_PASSWORD", "demo")
        response = client.post(
            "/login",
            data={"username": "rita.reviewer", "password": password},
            follow_redirects=False,
        )
        assert response.status_code == 303
        token = client.cookies[COOKIE_NAME]

        conn = sqlite3.connect(db_path)
        try:
            backdated = (datetime.now(timezone.utc) - timedelta(hours=9)).isoformat()
            conn.execute(
                "UPDATE sessions SET created_at = ? WHERE token = ?",
                (backdated, token),
            )
            conn.commit()
        finally:
            conn.close()

        assert client.get("/api/me").status_code == 401
        conn = sqlite3.connect(db_path)
        try:
            assert conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE token = ?", (token,)
            ).fetchone()[0] == 0
        finally:
            conn.close()


def test_sixth_failed_login_is_throttled_before_password_verification(tmp_path, monkeypatch):
    application = create_app(db_path=tmp_path / "login-throttle.db")
    password = os.environ.get("DEMO_PASSWORD", "demo")
    with TestClient(application) as client:
        for _ in range(5):
            response = client.post(
                "/login",
                data={"username": "nina.access", "password": "incorrect"},
                follow_redirects=False,
            )
            assert response.status_code == 200

        def unexpected_password_check(*args, **kwargs):
            pytest.fail("password verification ran for a throttled login")

        monkeypatch.setattr("app.main.verify_password", unexpected_password_check)
        response = client.post(
            "/login",
            data={"username": "nina.access", "password": password},
            follow_redirects=False,
        )
        assert response.status_code == 429
        assert "Too many sign-in attempts. Try again in 15 minutes." in response.text


def test_successful_login_clears_throttle_key(tmp_path):
    application = create_app(db_path=tmp_path / "login-clear.db")
    password = os.environ.get("DEMO_PASSWORD", "demo")
    with TestClient(application) as client:
        for _ in range(2):
            response = client.post(
                "/login",
                data={"username": "colin.claims", "password": "incorrect"},
                follow_redirects=False,
            )
            assert response.status_code == 200
        assert client.post(
            "/login",
            data={"username": "colin.claims", "password": password},
            follow_redirects=False,
        ).status_code == 303
        for _ in range(5):
            response = client.post(
                "/login",
                data={"username": "colin.claims", "password": "incorrect"},
                follow_redirects=False,
            )
            assert response.status_code == 200
        assert client.post(
            "/login",
            data={"username": "colin.claims", "password": password},
            follow_redirects=False,
        ).status_code == 429


def test_cookie_secure_defaults_to_request_scheme_and_honors_override(tmp_path, monkeypatch):
    application = create_app(db_path=tmp_path / "cookie-policy.db")
    password = os.environ.get("DEMO_PASSWORD", "demo")
    monkeypatch.delenv("PORTAL_COOKIE_SECURE", raising=False)
    with TestClient(application, base_url="http://testserver") as client:
        response = client.post(
            "/login",
            data={"username": "rita.reviewer", "password": password},
            follow_redirects=False,
        )
        cookie = response.headers["set-cookie"].lower()
        assert "httponly" in cookie
        assert "samesite=lax" in cookie
        assert "; secure" not in cookie
        deleted = client.post("/logout", follow_redirects=False).headers["set-cookie"].lower()
        assert "httponly" in deleted
        assert "samesite=lax" in deleted
        assert "; secure" not in deleted

    with TestClient(application, base_url="https://testserver") as client:
        response = client.post(
            "/login",
            data={"username": "rita.reviewer", "password": password},
            follow_redirects=False,
        )
        assert "; secure" in response.headers["set-cookie"].lower()

    monkeypatch.setenv("PORTAL_COOKIE_SECURE", "1")
    with TestClient(application, base_url="http://testserver") as client:
        response = client.post(
            "/login",
            data={"username": "fiona.flags", "password": password},
            follow_redirects=False,
        )
        assert "; secure" in response.headers["set-cookie"].lower()

    monkeypatch.setenv("PORTAL_COOKIE_SECURE", "0")
    with TestClient(application, base_url="https://testserver") as client:
        response = client.post(
            "/login",
            data={"username": "aaron.auditor", "password": password},
            follow_redirects=False,
        )
        assert "; secure" not in response.headers["set-cookie"].lower()


def test_demo_account_choices_can_be_hidden(tmp_path, monkeypatch):
    application = create_app(db_path=tmp_path / "demo-choices.db")
    with TestClient(application) as client:
        monkeypatch.delenv("SHOW_DEMO_ACCOUNTS", raising=False)
        default_page = client.get("/login")
        assert "Sign in as" in default_page.text
        assert (
            f"Password for all accounts: {os.environ.get('DEMO_PASSWORD', 'demo')}"
            in default_page.text
        )
        assert "Nina Okafor" in default_page.text

        monkeypatch.setenv("SHOW_DEMO_ACCOUNTS", "0")
        hidden_page = client.get("/login")
        assert "Sign in as" not in hidden_page.text
        assert "Password for all accounts" not in hidden_page.text
        assert "Nina Okafor" not in hidden_page.text
        assert "name=\"username\"" in hidden_page.text
