"""The four facts a listing shows beside its title, and the check each one passes.

Experience, salary, work mode and job type are read by whichever call reads the
posting — the brief for a scraped job, the parse for a captured page — and verified
here the same way for both: the model proposes, the page decides. A figure not in the
posting verbatim is dropped, and a work mode or job type needs a word that says so.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel

WorkMode = Literal["on_site", "hybrid", "remote"]
JobType = Literal["full_time", "contract", "part_time", "internship"]

# The job fields these land in, in the order the listing shows them.
DETAIL_FIELDS = ("experienceBand", "salaryText", "workMode", "jobType")

# Words that have to appear in the posting before a work mode or job type is believed.
MODE_WORDS = {
    "remote": r"\bremote\b|work from home|\bwfh\b",
    "hybrid": r"\bhybrid\b",
    "on_site": r"\bon[- ]?site\b|\bin[- ]office\b|work from office|\bwfo\b",
}
TYPE_WORDS = {
    "full_time": r"\bfull[- ]time\b|\bpermanent\b",
    "part_time": r"\bpart[- ]time\b",
    "contract": r"\bcontract(or|ual)?\b|\bfixed[- ]term\b",
    "internship": r"\bintern(ship)?\b",
}


class JobDetails(BaseModel):
    experience: str | None = None
    salary: str | None = None
    workMode: WorkMode | None = None
    jobType: JobType | None = None

    def as_job_fields(self) -> dict[str, str]:
        """The stated details under the names the job row stores them by."""
        fields = {
            "experienceBand": self.experience,
            "salaryText": self.salary,
            "workMode": self.workMode,
            "jobType": self.jobType,
        }
        return {name: value for name, value in fields.items() if value is not None}


def verify_details(proposed: JobDetails, text: str) -> JobDetails:
    flat = _flatten(text)
    return JobDetails(
        experience=proposed.experience if _verbatim(proposed.experience, flat) else None,
        salary=proposed.salary if _verbatim(proposed.salary, flat) else None,
        workMode=proposed.workMode if _said(MODE_WORDS, proposed.workMode, text) else None,
        jobType=proposed.jobType if _said(TYPE_WORDS, proposed.jobType, text) else None,
    )


def _verbatim(value: str | None, flat_text: str) -> bool:
    return bool(value) and _flatten(value) in flat_text


def _said(words: dict[str, str], value: str | None, text: str) -> bool:
    return value is not None and re.search(words[value], text, re.IGNORECASE) is not None


def _flatten(value: str) -> str:
    return " ".join(value.lower().split())


if __name__ == "__main__":
    print(
        verify_details(
            JobDetails(experience="6-10 years", salary="40 LPA", workMode="hybrid"),
            "We need 6-10 years of experience. Hybrid, Bengaluru.",
        )
    )
