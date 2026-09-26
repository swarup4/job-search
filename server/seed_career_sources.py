"""One-shot seed of the `career_sources` collection from `career_sources_seed.json`.

    python seed_career_sources.py

Rows are the Workday companies checked on 2026-09-24 (docs/08-Career-Page-Scraping.md
§3.1). A name already present is skipped, so re-running is safe and never undoes an
`enabled` you changed since.
"""

import asyncio
import json
from pathlib import Path

from config.database import connect, disconnect
from modules.career_source.models import CareerSource, CareerSourceCreate

SEED = Path(__file__).resolve().parent / "career_sources_seed.json"


async def main() -> None:
    await connect()
    added = skipped = 0

    for row in json.loads(SEED.read_text()):
        payload = CareerSourceCreate(**row)
        if await CareerSource.find_one(CareerSource.name == payload.name) is not None:
            skipped += 1
            continue
        await CareerSource(**payload.model_dump()).insert()
        state = "enabled " if payload.enabled else "disabled"
        print(f"  add  {state}  {payload.name}")
        added += 1

    print(f"{added} added, {skipped} already present")
    await disconnect()


if __name__ == "__main__":
    asyncio.run(main())
