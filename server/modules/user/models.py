from datetime import datetime

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field


class SignUp(BaseModel):
    name: str
    email: str
    password: str
    # Neither is the caller's to supply: there is no picture at signup, and a refresh
    # token is issued by the server, never sent to it.
    profilePicture: str | None = None
    refreshToken: str | None = None


class Login(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    # `_id` here was a Pydantic private attribute, not a field, so the id never
    # reached the client. `profilePicture` is optional because the document allows None.
    id: PydanticObjectId
    name: str
    email: str
    role: str | None = None
    profilePicture: str | None = None


class SignedUpUser(BaseModel):
    """Signup carries no picture and no role yet, so it returns neither."""

    id: PydanticObjectId
    name: str
    email: str


class SignUpResult(BaseModel):
    access_token: str
    user: SignedUpUser


class User(Document):
    name: str = Field(None, description="Name")
    email: str = Field(None, description="Email")
    password: str = Field(None, description="Password")
    profilePicture: str | None = Field(None, description="Profile Picture")
    status: bool = Field(default=True)
    refreshToken: str | None = Field(None, description="Refresh Token")
    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "users"
