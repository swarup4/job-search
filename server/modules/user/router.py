from fastapi import APIRouter

from modules.user import service
from modules.user.models import Login, SignUp, User

router = APIRouter()


@router.post("/login", response_model=User)
async def login(body: Login) -> User | None:
    return await service.login(body)


@router.post("/signup", response_model=User)
async def signup(body: SignUp) -> User:
    return await service.sign_up(body)


@router.get("/", response_model=list[User])
async def get_all_user() -> list[User]:
    return await service.get_user_list()
