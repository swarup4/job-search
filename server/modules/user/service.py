from modules.user.models import Login, SignUp, User


async def sign_up(user: SignUp) -> User:
    data = User(**user.model_dump())
    await data.insert()
    return data


async def login(user: Login) -> User | None:
    query: dict[str, str | bool] = {"status": True, **user.model_dump()}
    return await User.find_one(query)


async def get_user_list() -> list[User]:
    return await User.find_all().to_list()
