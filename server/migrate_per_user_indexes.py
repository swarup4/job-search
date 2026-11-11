"""One-shot replacement of two unique indexes that left `userId` out.

    python migrate_per_user_indexes.py            # dry run: report only
    python migrate_per_user_indexes.py --apply    # write

`jobs` is shared by every account, but `matches` was unique on `jobId` and `resumes`
on `(jobId, version)`, so only the first account to score or tailor a posting could.
The models now declare both per user. `init_beanie` creates the new indexes and
leaves the old ones standing, and an old unique index goes on refusing the second
account — so a database created before this change needs them dropped here.

Safe to run twice: an index already gone is skipped. Nothing is deleted from either
collection; rows the old indexes allowed are all valid under the new ones.
"""

import argparse
import asyncio
import os

from pymongo import ASCENDING, DESCENDING, AsyncMongoClient

import config  # noqa: F401 — loads server/.env

# collection -> (the old index's name, the new index's keys)
REPLACEMENTS = {
    "matches": ("jobId_1", [("userId", ASCENDING), ("jobId", ASCENDING)]),
    "resumes": (
        "jobId_1_version_-1",
        [("userId", ASCENDING), ("jobId", ASCENDING), ("version", DESCENDING)],
    ),
}


async def main(apply: bool) -> None:
    client = AsyncMongoClient(os.environ.get("MONGODB_URI", "mongodb://127.0.0.1:27017"))
    db = client[os.environ.get("MONGODB_DB_NAME", "jobpilot")]
    print(f"[{'APPLY' if apply else 'DRY RUN'}] database {db.name}")

    for name, (old, keys) in REPLACEMENTS.items():
        collection = db[name]
        existing = await collection.index_information()

        # Created first, so the collection is never without a uniqueness guarantee.
        described = ", ".join(field for field, _ in keys)
        print(f"  {name}: unique index on ({described})")
        if apply:
            await collection.create_index(keys, unique=True)

        if old in existing:
            print(f"  {name}: drop {old}")
            if apply:
                await collection.drop_index(old)
        else:
            print(f"  {name}: {old} is not there — nothing to drop")

    await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="write the changes")
    asyncio.run(main(parser.parse_args().apply))
