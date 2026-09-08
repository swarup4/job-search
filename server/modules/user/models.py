from datetime import datetime

from beanie import Document
from pydantic import BaseModel, Field


class SignUp(BaseModel):
    name: str
    email: str
    password: str
    profilePicture: str
    refreshToken: str


class Login(BaseModel):
    email: str
    password: str


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
