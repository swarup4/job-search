"""Public interface of the jobpilot_api tool server."""

from mcp_servers.jobpilot_api.client import (
    JobPilotApiError,
    NotSignedIn,
    get_base_resume,
    get_job,
    get_job_description,
    get_match,
    get_profile,
    list_new_jobs,
    reset_session,
    store_resume,
    write_match,
)

NAME = "jobpilot_api"

__all__ = [
    "NAME",
    "JobPilotApiError",
    "NotSignedIn",
    "get_base_resume",
    "get_job",
    "get_job_description",
    "get_match",
    "get_profile",
    "list_new_jobs",
    "reset_session",
    "store_resume",
    "write_match",
]
