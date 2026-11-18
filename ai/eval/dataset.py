"""The labelled set: postings, profiles, and what a correct reading of each looks like.

One JSON file holds the whole set, so a label and the text it labels cannot drift
apart. Labels are written by a person reading the posting and the profile — never
copied from a model's answer, which would measure the model against itself.

    {
      "postings": [{
        "id": "acme-platform",
        "jdText": "...the posting as stored...",
        "requirements": ["Kubernetes", "Terraform"],
        "details": {"experience": "6+ years", "workMode": "hybrid"},
        "verdicts": {"backend-dev": {"present": ["Kubernetes"], "missing": ["Terraform"]}}
      }],
      "profiles": [{"id": "backend-dev", "profile": {...as GET /profile returns it...}}]
    }
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from agents.details import JobDetails


class LabelledVerdicts(BaseModel):
    """For one posting and one profile: which requirements the profile really shows."""

    present: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)


class LabelledPosting(BaseModel):
    id: str
    title: str = ""
    company: str = ""
    location: str = ""
    jdText: str
    # Every concrete requirement the posting states, in its own wording.
    requirements: list[str]
    # The four details as the posting states them; a field it does not state is null.
    details: JobDetails = Field(default_factory=JobDetails)
    # Keyed by profile id. A profile with no entry is not judged against this posting.
    verdicts: dict[str, LabelledVerdicts] = Field(default_factory=dict)


class LabelledProfile(BaseModel):
    id: str
    profile: dict[str, Any]


class LabelledSet(BaseModel):
    postings: list[LabelledPosting]
    profiles: list[LabelledProfile] = Field(default_factory=list)

    def profile(self, profile_id: str) -> LabelledProfile | None:
        return next((item for item in self.profiles if item.id == profile_id), None)


def load(path: Path) -> LabelledSet:
    """One file, or every `*.json` in a folder merged — so a set can grow a file at a
    time without anyone editing a long one."""
    files = sorted(path.glob("*.json")) if path.is_dir() else [path]
    if not files:
        raise FileNotFoundError(f"no labelled set at {path}")
    merged = LabelledSet(postings=[], profiles=[])
    for file in files:
        part = LabelledSet.model_validate(json.loads(file.read_text(encoding="utf-8")))
        merged.postings.extend(part.postings)
        merged.profiles.extend(part.profiles)

    for kind, ids in (
        ("posting", [item.id for item in merged.postings]),
        ("profile", [item.id for item in merged.profiles]),
    ):
        repeated = sorted({item for item in ids if ids.count(item) > 1})
        if repeated:
            raise ValueError(f"{kind} ids repeated in the labelled set: {', '.join(repeated)}")
    return merged
