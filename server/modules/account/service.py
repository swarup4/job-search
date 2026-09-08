"""Signup and login rules, and this module's queries.

Imports no hashing library and no JWT library — only the two protocols. Swapping
argon2 for bcrypt, or JWT for sessions, does not touch this file (OCP).
"""

from errors import Conflict, DomainError
from modules.account.models import Account, AccountRead, Login, LoginResult, SignUp
from modules.account.security import PasswordHasher, TokenIssuer


class EmailAlreadyRegistered(Conflict):
    def __init__(self, email: str) -> None:
        super().__init__(f"an account already exists for {email}")


class InvalidCredentials(DomainError):
    status = 401

    def __init__(self) -> None:
        # Deliberately identical for an unknown email and a wrong password, so the
        # response cannot be used to enumerate accounts.
        super().__init__("email or password is incorrect")


class AccountService:
    def __init__(self, hasher: PasswordHasher, tokens: TokenIssuer) -> None:
        self._hasher = hasher
        self._tokens = tokens

    async def sign_up(self, payload: SignUp) -> Account:
        if await Account.find_one(Account.email == payload.email) is not None:
            raise EmailAlreadyRegistered(payload.email)

        account = Account(
            **payload.model_dump(exclude={"password"}),
            password_hash=self._hasher.hash(payload.password),
        )
        await account.insert()
        return account

    async def login(self, payload: Login) -> LoginResult:
        account = await Account.find_one({"email": payload.email, "active": True})
        if account is None or not self._hasher.verify(payload.password, account.password_hash):
            raise InvalidCredentials

        return LoginResult(
            access_token=self._tokens.issue(str(account.id)),
            account=AccountRead(**account.model_dump()),
        )

    async def list_accounts(self, limit: int = 50) -> list[Account]:
        return await Account.find({"active": True}).limit(limit).to_list()
