import hashlib
import hmac
import secrets
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request

from app.core.db import connect
from app.core.permissions import ROLE_PERMISSIONS


DEMO_USERS = (
    ("rita.reviewer", "Rita Reviewer", "reviewer"),
    ("colin.claims", "Colin Claims", "claims_operator"),
    ("fiona.flags", "Fiona Flags", "flag_operator"),
    ("aaron.auditor", "Aaron Auditor", "auditor"),
)
COOKIE_NAME = "portal_session"


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
        """SELECT users.id, users.username, users.display_name, users.role
           FROM sessions JOIN users ON users.id = sessions.user_id
           WHERE sessions.token = ?""",
        (token,),
    ).fetchone()
    return dict(row) if row else None


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
    def dependency(user=Depends(current_user)):
        if permission not in ROLE_PERMISSIONS.get(user["role"], set()):
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
