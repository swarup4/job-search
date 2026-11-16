"""Fill `experienceMin` and `experienceMax` on jobs stored before P3-33 parsed them.

    python backfill_job_experience.py            # dry run: report only
    python backfill_job_experience.py --apply    # write

Only jobs that have an `experienceBand` and no numbers yet are touched, so a re-run
changes nothing. The band itself is left exactly as it was.
"""

import argparse
import asyncio
import os
from collections import Counter

from pymongo import AsyncMongoClient, UpdateOne

import config  # noqa: F401 — loads server/.env
from modules.job.experience import parse_experience


async def main(apply: bool) -> None:
    client = AsyncMongoClient(os.environ.get("MONGODB_URI", "mongodb://127.0.0.1:27017"))
    db = client[os.environ.get("MONGODB_DB_NAME", "jobpilot")]
    print(f"[{'APPLY' if apply else 'DRY RUN'}] database {db.name}")

    pending = await db.jobs.find(
        {
            "experienceBand": {"$nin": [None, ""]},
            "$or": [{"experienceMin": None}, {"experienceMin": {"$exists": False}}],
        },
        {"experienceBand": 1},
    ).to_list()

    writes: list[UpdateOne] = []
    unread: Counter[str] = Counter()
    for job in pending:
        low, high = parse_experience(job["experienceBand"])
        if low is None:
            unread[job["experienceBand"]] += 1
            continue
        writes.append(
            UpdateOne({"_id": job["_id"]}, {"$set": {"experienceMin": low, "experienceMax": high}})
        )

    print(f"{len(pending)} jobs with a band and no numbers; {len(writes)} read")
    if unread:
        print("no figure read from:")
        for band, count in unread.most_common():
            print(f"  {count:>4}  {band!r}")

    if apply and writes:
        result = await db.jobs.bulk_write(writes)
        print(f"updated {result.modified_count}")
    await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="write the changes")
    asyncio.run(main(parser.parse_args().apply))
