"""Public interface of the job module. Nothing outside imports past this file."""

from modules.job.models import (
    Company,
    Job,
    JobCreate,
    JobCreated,
    JobRead,
    JobSource,
    JobStatus,
    JobType,
    JobUpdate,
    WorkMode,
)
from modules.job.router import router
from modules.job.service import JobNotFound, count_jobs, create_job, get_job, list_jobs, update_job

NAME = "job"

__all__ = [
    "NAME",
    "Company",
    "Job",
    "JobCreate",
    "JobCreated",
    "JobNotFound",
    "JobRead",
    "JobSource",
    "JobStatus",
    "JobType",
    "JobUpdate",
    "WorkMode",
    "count_jobs",
    "create_job",
    "get_job",
    "list_jobs",
    "router",
    "update_job",
]
