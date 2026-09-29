"""Fill `country` and `cities` on jobs stored before P3-31 read them on create.

    python backfill_job_locations.py            # dry run: report only
    python backfill_job_locations.py --apply    # write

Only jobs with no country yet are touched, so a re-run changes nothing and a country
a board supplied is never replaced. `location` itself is left exactly as it was.
"""

import argparse
import asyncio
import os
from collections import Counter

from pymongo import AsyncMongoClient, UpdateOne

import config  # noqa: F401 — loads server/.env
from modules.job.location import parse_location


async def main(apply: bool) -> None:
    client = AsyncMongoClient(os.environ.get("MONGODB_URI", "mongodb://127.0.0.1:27017"))
    db = client[os.environ.get("MONGODB_DB_NAME", "jobpilot")]
    print(f"[{'APPLY' if apply else 'DRY RUN'}] database {db.name}")

    pending = await db.jobs.find(
        {"$or": [{"country": None}, {"country": {"$exists": False}}]}, {"location": 1}
    ).to_list()

    writes: list[UpdateOne] = []
    countries: Counter[str] = Counter()
    unread: Counter[str] = Counter()
    for job in pending:
        location = job.get("location") or ""
        country, cities = parse_location(location)
        countries[country or "—"] += 1
        if country is None or not cities:
            unread[location] += 1
        writes.append(
            UpdateOne({"_id": job["_id"]}, {"$set": {"country": country, "cities": cities}})
        )

    print(f"{len(pending)} jobs without a country")
    for name, count in countries.most_common():
        print(f"  {count:>4}  {name}")
    if unread:
        print("no country or no city read from:")
        for location, count in unread.most_common():
            print(f"  {count:>4}  {location!r}")

    if apply and writes:
        result = await db.jobs.bulk_write(writes)
        print(f"updated {result.modified_count}")
    await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="write the changes")
    asyncio.run(main(parser.parse_args().apply))
