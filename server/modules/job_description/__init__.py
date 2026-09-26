"""Public interface of the job description module. Nothing outside imports past
this file."""

from modules.job_description.models import (
    CaptureRegion,
    DescriptionStatus,
    JobDescription,
)
from modules.job_description.router import router
from modules.job_description.service import (
    create_description,
    get_description,
    get_for_job,
    link_to_job,
)

NAME = "job-description"

__all__ = [
    "NAME",
    "CaptureRegion",
    "DescriptionStatus",
    "JobDescription",
    "create_description",
    "get_description",
    "get_for_job",
    "link_to_job",
    "router",
]
