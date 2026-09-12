"""Signup, login, refresh, and this module's queries."""

from beanie import PydanticObjectId

from config.errors import Conflict, NotFound, Unauthorized
from modules.account.models import (
    Account,
    AccountRead,
    AccountUpdate,
    Login,
    LoginResult,
    Refresh,
    SignUp,
)
from modules.account.security import (
    ACCESS,
    REFRESH,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)


def _signed_in(account: Account) -> LoginResult:
    """What every way of becoming signed in answers with, so the dashboard stores
    the result the same way whichever call produced it."""
    return LoginResult(
        access_token=create_token(str(account.id), ACCESS),
        refresh_token=create_token(str(account.id), REFRESH),
        account=AccountRead(**account.model_dump()),
    )


async def sign_up(payload: SignUp) -> LoginResult:
    """Signing up signs you in: the caller gets the same result as a login, so
    there is no second round trip to post the credentials again."""
    if await Account.find_one(Account.email == payload.email) is not None:
        raise Conflict(f"an account already exists for {payload.email}")

    account = Account(
        **payload.model_dump(exclude={"password"}),
        password_hash=hash_password(payload.password),
    )
    await account.insert()
    return _signed_in(account)


async def login(payload: Login) -> LoginResult:
    account = await Account.find_one({"email": payload.email, "active": True})
    if account is None or not verify_password(payload.password, account.password_hash):
        # Deliberately identical for an unknown email and a wrong password, so the
        # response cannot be used to find out which addresses are registered.
        raise Unauthorized("email or password is incorrect")

    return _signed_in(account)


async def refresh(payload: Refresh) -> LoginResult:
    """Trades a refresh token for a new pair.

    The new refresh token replaces the one just spent, so a session in daily use
    never has to sign in again while one left idle past the refresh lifetime does.
    """
    token = decode_token(payload.refresh_token)
    if token["kind"] != REFRESH:
        raise Unauthorized("token is invalid or has expired")

    account = await Account.get(PydanticObjectId(token["sub"]))
    if account is None or not account.active:
        raise Unauthorized("token is invalid or has expired")

    return _signed_in(account)


async def get_account(account_id: PydanticObjectId) -> Account:
    account = await Account.get(account_id)
    if account is None:
        raise NotFound(f"account {account_id} not found")
    return account


async def update_account(account_id: PydanticObjectId, payload: AccountUpdate) -> Account:
    account = await get_account(account_id)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(account, field, value)
    await account.save()
    return account
