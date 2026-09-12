from config.errors import DomainError
from modules.account import TokenIssuer
from modules.user.models import Login, SignedUpUser, SignUp, SignUpResult, User


class InvalidCredentials(DomainError):
    status = 401

    def __init__(self) -> None:
        # Identical for an unknown email and a wrong password, so the response
        # cannot be used to find out which addresses are registered.
        super().__init__("email or password is incorrect")


async def sign_up(user: SignUp, tokens: TokenIssuer) -> SignUpResult:
    """Signing up signs you in: the caller gets a token rather than having to post
    the same credentials again."""
    data = User(**user.model_dump())
    await data.insert()
    return SignUpResult(
        access_token=tokens.issue(str(data.id)),
        user=SignedUpUser(id=data.id, name=data.name, email=data.email),
    )


async def login(user: Login) -> User:
    query: dict[str, str | bool] = {"status": True, **user.model_dump()}
    found = await User.find_one(query)
    if found is None:
        # Returning None here is what made a failed login a 500: the response model
        # has no way to serialise it.
        raise InvalidCredentials
    return found


async def get_user_list() -> list[User]:
    return await User.find_all().to_list()
