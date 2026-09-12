"""Everything about authentication: hashing passwords, making and reading tokens,
and the one guard the routers hang off."""

import os
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from beanie import PydanticObjectId
from fastapi import Depends, Header
from pwdlib import PasswordHash
from pwdlib.exceptions import PwdlibError

from config.errors import Unauthorized

# Written into the token and checked when it comes back, so a refresh token cannot
# be used in place of an access token.
ACCESS = "access"
REFRESH = "refresh"

ALGORITHM = "HS256"

# Read once at import; `config/__init__.py` has already loaded server/.env by then.
# The fallback is a placeholder, not a secret — seeing it means JWT_SECRET is missing.
SECRET = os.environ.get("JWT_SECRET", "jobpilot-jwt-secret-missing-from-dot-env")
ACCESS_TTL = timedelta(minutes=int(os.environ.get("JWT_TTL_MINUTES", "60")))
REFRESH_TTL = timedelta(days=int(os.environ.get("JWT_REFRESH_TTL_DAYS", "30")))

_passwords = PasswordHash.recommended()

BEARER = "Bearer "


def hash_password(password: str) -> str:
    return _passwords.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _passwords.verify(password, password_hash)
    except PwdlibError:
        # pwdlib raises on a hash it cannot read. That is a failed login, not a 500.
        return False


def create_token(account_id: str, kind: str) -> str:
    ttl = ACCESS_TTL if kind == ACCESS else REFRESH_TTL
    payload = {"sub": account_id, "kind": kind, "exp": datetime.now(UTC) + ttl}
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Checks the signature and the expiry, then hands back what is inside."""
    try:
        return jwt.decode(token, SECRET, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise Unauthorized("token is invalid or has expired") from None


async def verify_token(
    authorization: Annotated[str | None, Header()] = None,
) -> PydanticObjectId:
    """The id of the signed-in user, read straight off `Authorization: Bearer <token>`."""
    if not authorization or not authorization.startswith(BEARER):
        raise Unauthorized("sign in first")

    payload = decode_token(authorization.removeprefix(BEARER).strip())
    if payload["kind"] != ACCESS:
        raise Unauthorized("token is invalid or has expired")

    return PydanticObjectId(payload["sub"])


# A route that works on your own data writes `user_id: CurrentUser` and gets the id.
# A router whose routes only need a signed-in caller writes `Depends(verify_token)`
# instead, which runs the same check but discards the id.
CurrentUser = Annotated[PydanticObjectId, Depends(verify_token)]
