"""Remove `job_descriptions.requirements`, which P3-32 replaced with `jobs.techStack`.

    python migrate_drop_description_requirements.py            # dry run: report only
    python migrate_drop_description_requirements.py --apply    # write

The old lists are not copied across: the match step wrote every requirement it found,
qualifications included ("3 years LLM experience"), so they are not a tech stack. Each
job keeps `techStack` null and gets a real one the next time it is analyzed.
"""

import argparse
import asyncio
import os

from pymongo import AsyncMongoClient

import config  # noqa: F401 — loads server/.env


async def main(apply: bool) -> None:
    client = AsyncMongoClient(os.environ.get("MONGODB_URI", "mongodb://127.0.0.1:27017"))
    db = client[os.environ.get("MONGODB_DB_NAME", "jobpilot")]
    print(f"[{'APPLY' if apply else 'DRY RUN'}] database {db.name}")

    carrying = {"requirements": {"$exists": True}}
    total = await db.job_descriptions.count_documents(carrying)
    filled = await db.job_descriptions.find(
        {"requirements.0": {"$exists": True}}, {"jobId": 1, "requirements": 1}
    ).to_list()
    print(f"{total} descriptions carry `requirements`, {len(filled)} of them non-empty:")
    for row in filled:
        print(f"  job {row.get('jobId')}: {row['requirements']}")

    if apply and total:
        result = await db.job_descriptions.update_many(carrying, {"$unset": {"requirements": ""}})
        print(f"unset on {result.modified_count}")
    await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="write the changes")
    asyncio.run(main(parser.parse_args().apply))
