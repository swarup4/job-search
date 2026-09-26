"""One-shot move of the per-user pipeline off the shared `jobs` collection.

    python migrate_pipeline_to_applications.py            # dry run: report only
    python migrate_pipeline_to_applications.py --apply    # write
    python migrate_pipeline_to_applications.py --apply --account you@example.com

Run it before starting the server on the new code: `init_beanie` cannot create the
unique `(userId, jobId)` index over the old non-unique one of the same name, so this
uses the driver directly rather than `config.database.connect()`.

- `jobs.shortlisted: true` becomes a `shortlisted` application for the account.
- `jobs.status: reviewed` is dropped, not migrated: analysis set it, not the user, and
  a scored job stays in New until it is shortlisted.
- `tailored` / `applied` jobs already have the application their resume staged.
- `status` and `shortlisted` are then unset from every job, and the old indexes dropped.
"""

import argparse
import asyncio
import os
from datetime import UTC, datetime

from pymongo import ASCENDING, AsyncMongoClient

import config  # noqa: F401 — loads server/.env

OLD_JOB_INDEX = "status_1_discoveredAt_-1"
PAIR_INDEX = "userId_1_jobId_1"


async def main(apply: bool, email: str | None) -> None:
    client = AsyncMongoClient(os.environ.get("MONGODB_URI", "mongodb://127.0.0.1:27017"))
    db = client[os.environ.get("MONGODB_DB_NAME", "jobpilot")]
    mode = "APPLY" if apply else "DRY RUN"
    print(f"[{mode}] database {db.name}")

    accounts = await db.accounts.find({} if email is None else {"email": email}).to_list()
    if len(accounts) != 1:
        found = ", ".join(account["email"] for account in accounts) or "none"
        raise SystemExit(f"need exactly one account, found: {found} — pass --account <email>")
    user_id = accounts[0]["_id"]
    print(f"account {accounts[0]['email']}")

    duplicates = await (
        await db.applications.aggregate(
            [
                {"$group": {"_id": {"u": "$userId", "j": "$jobId"}, "n": {"$sum": 1}}},
                {"$match": {"n": {"$gt": 1}}},
            ]
        )
    ).to_list()
    if duplicates:
        for row in duplicates:
            print(f"  duplicate  user {row['_id']['u']}  job {row['_id']['j']}  ×{row['n']}")
        raise SystemExit("resolve the duplicate applications above first; nothing was written")

    started = {row["jobId"] for row in await db.applications.find({"userId": user_id}).to_list()}
    shortlisted = await db.jobs.find({"shortlisted": True}).to_list()
    to_create = [job for job in shortlisted if job["_id"] not in started]
    for job in to_create:
        print(f"  shortlist  {job['title']} — {job['company']}")

    orphans = await db.jobs.find(
        {"status": {"$in": ["tailored", "applied"]}, "_id": {"$nin": list(started)}}
    ).to_list()
    for job in orphans:
        print(f"  no application for {job['status']} job {job['_id']} ({job['title']}) — left alone")

    backfill = await db.applications.count_documents({"shortlistedAt": {"$exists": False}})
    carrying = await db.jobs.count_documents(
        {"$or": [{"status": {"$exists": True}}, {"shortlisted": {"$exists": True}}]}
    )
    job_indexes = [index["name"] async for index in await db.jobs.list_indexes()]
    application_indexes = {index["name"]: index async for index in await db.applications.list_indexes()}
    pair = application_indexes.get(PAIR_INDEX)

    print(
        f"{len(to_create)} applications to create, {backfill} to backfill shortlistedAt, "
        f"{carrying} jobs to unset"
    )
    if OLD_JOB_INDEX in job_indexes:
        print(f"  drop jobs.{OLD_JOB_INDEX}")
    if pair is not None and not pair.get("unique"):
        print(f"  rebuild applications.{PAIR_INDEX} as unique")

    if not apply:
        print("dry run — re-run with --apply to write")
        await client.close()
        return

    now = datetime.now(UTC)
    if to_create:
        await db.applications.insert_many(
            [
                {
                    "userId": user_id,
                    "jobId": job["_id"],
                    "status": "shortlisted",
                    "ats": "other",
                    "fieldsFilled": [],
                    "screeningAnswers": [],
                    "approvedByUser": False,
                    "shortlistedAt": job.get("updatedAt", now),
                }
                for job in to_create
            ]
        )
    # Rows staged before shortlisting existed were started when they were staged.
    await db.applications.update_many(
        {"shortlistedAt": {"$exists": False}}, [{"$set": {"shortlistedAt": "$stagedAt"}}]
    )
    await db.jobs.update_many({}, {"$unset": {"status": "", "shortlisted": ""}})

    if OLD_JOB_INDEX in job_indexes:
        await db.jobs.drop_index(OLD_JOB_INDEX)
    if pair is not None and not pair.get("unique"):
        await db.applications.drop_index(PAIR_INDEX)
    await db.applications.create_index(
        [("userId", ASCENDING), ("jobId", ASCENDING)], name=PAIR_INDEX, unique=True
    )
    print("done")
    await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write; the default only reports")
    parser.add_argument("--account", help="the account's email, when there is more than one")
    arguments = parser.parse_args()
    asyncio.run(main(arguments.apply, arguments.account))
