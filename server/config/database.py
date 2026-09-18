import os

from beanie import init_beanie
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from modules.account import Account
from modules.application import AnswerBank, ApplicantProfile, Application
from modules.event import Event
from modules.job import Job
from modules.match import Match
from modules.profile import Certification, Education, Experience, Profile, Skill
from modules.resume import BaseResume, TailoredResume
from modules.template import Template

_client: AsyncMongoClient | None = None


def document_models() -> list[type]:
    """Every Beanie document in the local store, through its module's public interface."""
    return [
        Job,
        Match,
        TailoredResume,
        BaseResume,
        Application,
        AnswerBank,
        ApplicantProfile,
        Event,
        Profile,
        Experience,
        Education,
        Skill,
        Certification,
        Account,
        Template,
    ]


async def connect(db_name: str | None = None) -> AsyncDatabase:
    """The only place a Mongo client is opened.

    `db_name` exists for the test suite, which points the same app at a throwaway
    database rather than mocking the driver — see server-api.md."""
    global _client

    # uri = os.environ.get("MONGODB_LOCAL_URI", "mongodb://127.0.0.1:27017")
    uri = os.environ.get("MONGODB_URI", "mongodb://127.0.0.1:27017")
    # # mongodb+srv is Atlas. server has no business reaching the vector store.
    # if uri.startswith("mongodb+srv://"):
    #     raise RuntimeError("server may only connect to the local MongoDB, never Atlas")

    _client = AsyncMongoClient(uri)
    database = _client[db_name or os.environ.get("MONGODB_DB_NAME", "jobpilot")]
    await init_beanie(database=database, document_models=document_models())
    return database


async def disconnect() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
