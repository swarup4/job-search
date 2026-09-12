import os
from functools import lru_cache

from fastapi import APIRouter, Depends

from modules.account import JwtIssuer, TokenIssuer
from modules.user import service
from modules.user.models import Login, SignUp, SignUpResult, User, UserResponse

router = APIRouter(tags=["user"])


# The composition root: the only place a concrete issuer is named, and the only place
# the secret is read.
@lru_cache(maxsize=1)
def get_tokens() -> TokenIssuer:
    secret = os.environ.get("JWT_SECRET", "")
    if len(secret) < 32:
        raise RuntimeError("JWT_SECRET must be set in server/.env and be at least 32 characters")
    return JwtIssuer(secret, ttl_minutes=int(os.environ.get("JWT_TTL_MINUTES", "60")))


@router.post("/login", response_model=UserResponse)
async def login(body: Login) -> User:
    return await service.login(body)


@router.post("/signup", response_model=SignUpResult)
async def signup(body: SignUp, tokens: TokenIssuer = Depends(get_tokens)) -> SignUpResult:
    return await service.sign_up(body, tokens)


@router.get("/", response_model=list[UserResponse])
async def get_all_user() -> list[User]:
    return await service.get_user_list()
