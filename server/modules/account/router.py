from fastapi import APIRouter, status

from modules.account import service
from modules.account.models import (
    Account,
    AccountRead,
    AccountUpdate,
    Login,
    LoginResult,
    Refresh,
    SignUp,
)
from modules.account.security import CurrentUser

router = APIRouter(tags=["account"])

# Signup, login and refresh are the only routes with no token requirement — they
# are how you get one. Every other route in the API asks for `CurrentUser`.


@router.post("/signup", response_model=LoginResult, status_code=status.HTTP_201_CREATED)
async def sign_up(payload: SignUp) -> LoginResult:
    return await service.sign_up(payload)


@router.post("/login", response_model=LoginResult)
async def login(payload: Login) -> LoginResult:
    return await service.login(payload)


@router.post("/refresh", response_model=LoginResult)
async def refresh(payload: Refresh) -> LoginResult:
    return await service.refresh(payload)


@router.get("/getAccount", response_model=AccountRead)
async def get_account(user_id: CurrentUser) -> Account:
    return await service.get_account(user_id)


@router.patch("/updateAccount", response_model=AccountRead)
async def update_account(payload: AccountUpdate, user_id: CurrentUser) -> Account:
    return await service.update_account(user_id, payload)
