import os

from beanie import init_beanie
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.operations import SearchIndexModel

from modules.account import Account
from modules.application import AnswerBank, ApplicantProfile, Application
from modules.job import Job
from modules.job_description import JobDescription
from modules.match import Match
from modules.profile import Certification, Education, Experience, Profile, Skill
from modules.resume import BaseResume, TailoredResume
from modules.template import Template

_client: AsyncMongoClient | None = None

VECTOR_INDEX = "jd_embedding_index"
# `rag/embeddings.py` passes no `output_dimension`, so voyage-4-lite returns its
# default. A mismatch here is not an error, it is a search that never matches.
EMBEDDING_DIMS = 1024


def document_models() -> list[type]:
    """Every Beanie document, through its module's public interface."""
    return [
        Job,
        JobDescription,
        Match,
        TailoredResume,
        BaseResume,
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
        await _ensure_vector_index(database)
    return database


async def _ensure_vector_index(database: AsyncDatabase) -> None:
    """Create the `$vectorSearch` index on `job_descriptions.embedding` if it is
    missing. Atlas only — a local MongoDB has no such command."""
    existing = [
        index["name"] async for index in await database.job_descriptions.list_search_indexes()
    ]
    if VECTOR_INDEX in existing:
        return

    await database.job_descriptions.create_search_index(
        SearchIndexModel(
            name=VECTOR_INDEX,
            type="vectorSearch",
            definition={
                "fields": [
                    {
                        "type": "vector",
                        "path": "embedding",
                        "numDimensions": EMBEDDING_DIMS,
                        "similarity": "cosine",
                    }
                ]
            },
        )
    )


async def disconnect() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
