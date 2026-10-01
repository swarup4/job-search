import os

from beanie import init_beanie
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.operations import SearchIndexModel

from modules.account import Account
from modules.application import AnswerBank, ApplicantProfile, Application
from modules.career_source import CareerSource
from modules.job import Job
from modules.job_description import JobDescription
from modules.match import Match
from modules.preference import Preference
from modules.profile import Certification, Education, Experience, Profile, Skill
from modules.resume import BaseResume, TailoredResume
from modules.resume_chunk import VECTOR_INDEX as CHUNK_INDEX
from modules.resume_chunk import ResumeChunk
from modules.skill_inventory import SkillInventory
from modules.template import Template

_client: AsyncMongoClient | None = None

JD_INDEX = "jd_embedding_index"
# Both vector indexes and `rag/embeddings.py` have to agree on this. A mismatch is
# not an error, it is a search that never matches.
EMBEDDING_DIMS = 1024


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
    ]


async def connect(db_name: str | None = None) -> AsyncDatabase:
    """The only place a Mongo client is opened.

    `db_name` exists for the test suite, which points the same app at a throwaway
    database rather than mocking the driver — see server-api.md."""
    global _client

    # One store, Atlas. The vector lives on `job_descriptions` alongside its text,
    # so there is no second connection to keep the server out of any more.
    uri = os.environ.get("MONGODB_URI", "mongodb://127.0.0.1:27017")

    _client = AsyncMongoClient(uri)
    database = _client[db_name or os.environ.get("MONGODB_DB_NAME", "jobpilot")]
    await init_beanie(database=database, document_models=document_models())

    # Beanie manages ordinary indexes and knows nothing about Atlas search indexes,
    # so without this a fresh database has no vector search at all.
    if uri.startswith("mongodb+srv://"):
        await _ensure_vector_index(database, "job_descriptions", JD_INDEX)
        # Chunks are per-user, so this one carries a filter field. Filtering after an
        # approximate search returns fewer rows than asked for, or none — it has to
        # be part of the index. (P6-06)
        await _ensure_vector_index(database, "resume_chunks", CHUNK_INDEX, filters=["userId"])
    return database


async def _ensure_vector_index(
    database: AsyncDatabase,
    collection: str,
    name: str,
    filters: list[str] | None = None,
) -> None:
    """Create a `$vectorSearch` index on `<collection>.embedding` if it is missing.
    Atlas only — a local MongoDB has no such command."""
    existing = [index["name"] async for index in await database[collection].list_search_indexes()]
    if name in existing:
        return

    fields: list[dict[str, object]] = [
        {
            "type": "vector",
            "path": "embedding",
            "numDimensions": EMBEDDING_DIMS,
            "similarity": "cosine",
        }
    ]
    fields.extend({"type": "filter", "path": path} for path in filters or [])

    await database[collection].create_search_index(
        SearchIndexModel(name=name, type="vectorSearch", definition={"fields": fields})
    )


async def disconnect() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
