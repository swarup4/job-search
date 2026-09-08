import os

from beanie import init_beanie
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from modules.application import AnswerBank, Application
from modules.event import Event
from modules.job import Job
from modules.match import Match
from modules.profile import Profile, ResumeChunkText
from modules.resume import TailoredResume
from modules.user import User

_client: AsyncMongoClient | None = None


def document_models() -> list[type]:
    """Every Beanie document in the local store, through its module's public interface."""
    return [Job, Match, TailoredResume, Application, AnswerBank, Event, Profile, ResumeChunkText, User]


async def connect() -> AsyncDatabase:
    """The only place a Mongo client is opened."""
    global _client

    uri = os.environ.get("MONGODB_LOCAL_URI", "mongodb://127.0.0.1:27017")
    # # mongodb+srv is Atlas. server has no business reaching the vector store.
    # if uri.startswith("mongodb+srv://"):
    #     raise RuntimeError("server may only connect to the local MongoDB, never Atlas")

    _client = AsyncMongoClient(uri)
    database = _client[os.environ.get("MONGODB_DB_NAME", "jobpilot")]
    await init_beanie(database=database, document_models=document_models())
    return database


async def disconnect() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
