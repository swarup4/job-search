"""Password hashing and token issuing — the parts that change for security reasons
rather than product reasons (SRP).

Two small protocols rather than one `SecurityService`, so `AccountService` sees only
what it uses (ISP), and neither implementation is imported by the service (DIP).
"""

import datetime as dt
from typing import Protocol

import jwt
from pwdlib import PasswordHash
from pwdlib.exceptions import PwdlibError


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, password_hash: str) -> bool:
        """Contract every implementation must keep (LSP): returns False for a hash it
        cannot read. It never raises — a legacy or corrupt row is a failed login, not
        a 500."""
        ...


class TokenIssuer(Protocol):
    def issue(self, subject: str) -> str: ...


class Argon2Hasher:
    def __init__(self) -> None:
        self._context = PasswordHash.recommended()

    def hash(self, password: str) -> str:
        return self._context.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        try:
            return self._context.verify(password, password_hash)
        except PwdlibError:
            # pwdlib raises UnknownHashError on a hash it doesn't recognise — which the
            # plaintext rows in the old `users` collection are. Keep the contract above.
            return False


class JwtIssuer:
    def __init__(self, secret: str, ttl_minutes: int = 60, algorithm: str = "HS256") -> None:
        self._secret = secret
        self._ttl = dt.timedelta(minutes=ttl_minutes)
        self._algorithm = algorithm

    def issue(self, subject: str) -> str:
        payload = {"sub": subject, "exp": dt.datetime.now(dt.UTC) + self._ttl}
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)
