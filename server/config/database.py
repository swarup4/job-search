import os

from beanie import init_beanie
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from modules.account import Account
from modules.application import AnswerBank, ApplicantProfile, Application
from modules.career_source import CareerSource
from modules.job import Job
from modules.job_description import JobDescription
from modules.llm_usage import LlmUsage
from modules.match import Match
from modules.preference import Preference
from modules.profile import Certification, Education, Experience, Profile, Skill
from modules.resume import BaseResume, TailoredResume
from modules.resume_chunk import ResumeChunk
from modules.skill_inventory import SkillInventory
from modules.template import Template

_client: AsyncMongoClient | None = None


def document_models() -> list[type]:
    """Every Beanie document, through its module's public interface."""
    return [
        Job,
        JobDescription,
        Match,
        TailoredResume,
        BaseResume,
        ResumeChunk,
        SkillInventory,
        Application,
        AnswerBank,
        ApplicantProfile,
        Profile,
        Experience,
        Education,
        Skill,
        Certification,
        Account,
        Template,
        CareerSource,
        Preference,
        LlmUsage,
    ]


async def connect(db_name: str | None = None) -> AsyncDatabase:
    """The only place a Mongo client is opened.

    `db_name` exists for the test suite, which points the same app at a throwaway
    database rather than mocking the driver — see server-api.md."""
    global _client

    # One store, and any MongoDB will do. Vector search is an exact cosine in
    # `modules/resume_chunk`, so nothing here needs a search index or a hosted cluster.
    uri = os.environ.get("MONGODB_URI", "mongodb://127.0.0.1:27017")

    _client = AsyncMongoClient(uri)
    database = _client[db_name or os.environ.get("MONGODB_DB_NAME", "jobpilot")]
    await init_beanie(database=database, document_models=document_models())

    return database


async def disconnect() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
