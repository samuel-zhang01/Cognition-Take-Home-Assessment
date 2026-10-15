import hashlib
import hmac
import secrets
import os
import threading
import time
from collections import deque
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request

from app.core.db import connect
from app.core.controls import record_control_event
from app.core.permissions import ROLE_PERMISSIONS


DEMO_USERS = (
    ("rita.reviewer", "Rita Patel", "reviewer"),
    ("colin.claims", "Colin Murray", "claims_operator"),
    ("fiona.flags", "Fiona Grant", "flag_operator"),
    ("aaron.auditor", "Aaron Lee", "auditor"),
    ("nina.access", "Nina Okafor", "access_reviewer"),
)
COOKIE_NAME = "portal_session"
COOKIE_SECURE = os.environ.get("PORTAL_COOKIE_SECURE")
SESSION_TTL_HOURS = float(os.environ.get("SESSION_TTL_HOURS", "8"))
LOGIN_ATTEMPT_LIMIT = 5
LOGIN_WINDOW_SECONDS = 15 * 60
_login_failures = {}
_login_failures_lock = threading.Lock()
_login_attempt_locks = {}
_login_attempt_locks_guard = threading.Lock()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), 120_000
    ).hex()
    return salt, digest


def verify_password(password, salt, expected):
    _, actual = hash_password(password, salt)
    return hmac.compare_digest(actual, expected)


def find_session_user(conn, token):
    if not token:
        return None
    row = conn.execute(
        """SELECT users.id, users.username, users.display_name, users.role,
                  sessions.created_at AS session_created_at
           FROM sessions JOIN users ON users.id = sessions.user_id
           WHERE sessions.token = ?""",
        (token,),
    ).fetchone()
    if row is None:
        return None
    try:
        created_at = datetime.fromisoformat(row["session_created_at"].replace("Z", "+00:00"))
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        expired = created_at <= datetime.now(timezone.utc) - timedelta(
            hours=SESSION_TTL_HOURS
        )
    except (TypeError, ValueError):
        expired = True
    if expired:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        return None
    user = dict(row)
    del user["session_created_at"]
    return user


def _login_key(username, client_ip):
    return username.lower(), client_ip


@contextmanager
def login_attempt_lock(username, client_ip):
    key = _login_key(username, client_ip)
    with _login_attempt_locks_guard:
        state = _login_attempt_locks.get(key)
        if state is None:
            state = {"lock": threading.Lock(), "users": 0}
            _login_attempt_locks[key] = state
        state["users"] += 1
    try:
        with state["lock"]:
            yield
    finally:
        with _login_attempt_locks_guard:
            state["users"] -= 1
            if state["users"] == 0:
                _login_attempt_locks.pop(key, None)


def _prune_login_failures(now):
    for key, attempts in tuple(_login_failures.items()):
        while attempts and now - attempts[0] >= LOGIN_WINDOW_SECONDS:
            attempts.popleft()
        if not attempts:
            _login_failures.pop(key, None)


def login_attempt_allowed(username, client_ip):
    now = time.monotonic()
    key = _login_key(username, client_ip)
    with _login_failures_lock:
        _prune_login_failures(now)
        attempts = _login_failures.setdefault(key, deque())
        if len(attempts) >= LOGIN_ATTEMPT_LIMIT:
            return False
        attempts.append(now)
        return True


def clear_login_failures(username, client_ip):
    key = _login_key(username, client_ip)
    with _login_failures_lock:
        _login_failures.pop(key, None)


def cookie_secure(request):
    configured = os.environ.get("PORTAL_COOKIE_SECURE", COOKIE_SECURE)
    if configured == "1":
        return True
    if configured == "0":
        return False
    return request.url.scheme == "https"


def get_connection(request: Request):
    conn = connect(request.app.state.db_path)
    try:
        yield conn
    finally:
        conn.close()


def current_user(request: Request, conn=Depends(get_connection)):
    user = find_session_user(conn, request.cookies.get(COOKIE_NAME))
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def require_permission(permission):
    def dependency(
        request: Request,
        conn=Depends(get_connection),
        user=Depends(current_user),
    ):
        if permission not in ROLE_PERMISSIONS.get(user["role"], set()):
            module = {
                "counterparty": "counterparties",
                "claim": "claims",
                "flag": "flags",
                "access_reviews": "access_reviews",
                "audit": "audit",
            }.get(permission.split(".", 1)[0], permission.split(".", 1)[0])
            resource_id = next(iter(request.path_params.values()), "")
            record_control_event(conn, user, module, resource_id, "forbidden")
            raise HTTPException(status_code=403, detail="Permission denied")
        return user

    return dependency


def public_identity(user):
    return {
        "username": user["username"],
        "display_name": user["display_name"],
        "role": user["role"],
        "permissions": sorted(ROLE_PERMISSIONS[user["role"]]),
    }
