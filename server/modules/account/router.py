import os
from functools import lru_cache

from fastapi import APIRouter, Depends, Query, status

from modules.account.models import Account, AccountRead, Login, LoginResult, SignUp
from modules.account.security import Argon2Hasher, JwtIssuer
from modules.account.service import AccountService

router = APIRouter(tags=["account"])


# The composition root: the only place concrete classes are named. Config is read here
# because choosing the secret is a wiring decision, not a domain rule.
@lru_cache(maxsize=1)
def get_service() -> AccountService:
    secret = os.environ.get("JWT_SECRET", "")
    if len(secret) < 32:
        raise RuntimeError("JWT_SECRET must be set in server/.env and be at least 32 characters")
    return AccountService(
        hasher=Argon2Hasher(),
        tokens=JwtIssuer(secret, ttl_minutes=int(os.environ.get("JWT_TTL_MINUTES", "60"))),
    )


@router.post("/signup", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
async def sign_up(payload: SignUp, service: AccountService = Depends(get_service)) -> Account:
    return await service.sign_up(payload)


@router.post("/login", response_model=LoginResult)
async def login(payload: Login, service: AccountService = Depends(get_service)) -> LoginResult:
    return await service.login(payload)


@router.get("", response_model=list[AccountRead])
async def list_accounts(
    limit: int = Query(default=50, le=200),
    service: AccountService = Depends(get_service),
) -> list[Account]:
    return await service.list_accounts(limit)
