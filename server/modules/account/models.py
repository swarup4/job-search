from datetime import UTC, datetime

import pymongo
from beanie import Document, PydanticObjectId
from pydantic import BaseModel, EmailStr, Field


class Account(Document):
    name: str
    email: EmailStr
    password_hash: str
    profile_picture: str | None = None
    active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "accounts"
        indexes = [pymongo.IndexModel([("email", pymongo.ASCENDING)], unique=True)]


class SignUp(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=8)
    profile_picture: str | None = None


class Login(BaseModel):
    email: EmailStr
    password: str


class AccountRead(BaseModel):
    id: PydanticObjectId
    name: str
    email: EmailStr
    profile_picture: str | None


class LoginResult(BaseModel):
    access_token: str
    token_type: str = "bearer"
    account: AccountRead
