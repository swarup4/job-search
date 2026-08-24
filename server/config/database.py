from __future__ import annotations

from beanie import init_beanie
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from config.settings import get_settings

_client: AsyncMongoClient | None = None


def document_models() -> list[type]:
    """Every Beanie document in the local store, imported through its module's
    public interface."""
    from modules.application import AnswerBank, Application
    from modules.event import Event
    from modules.job import Job
    from modules.match import Match
    from modules.profile import Profile, ResumeChunkText
    from modules.resume import TailoredResume

    return [Job, Match, TailoredResume, Application, AnswerBank, Event, Profile, ResumeChunkText]


async def connect() -> AsyncDatabase:
    """The only place a Mongo client is opened."""
    global _client
    settings = get_settings()

    # mongodb+srv is Atlas. server has no business reaching the vector store.
    if settings.mongodb_local_uri.startswith("mongodb+srv://"):
        raise RuntimeError("server may only connect to the local MongoDB, never Atlas")

    _client = AsyncMongoClient(settings.mongodb_local_uri)
    database = _client[settings.mongodb_db_name]
    await init_beanie(database=database, document_models=document_models())
    return database


async def disconnect() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
