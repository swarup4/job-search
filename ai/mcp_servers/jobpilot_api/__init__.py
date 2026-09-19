"""Public interface of the jobpilot_api tool server."""

from mcp_servers.jobpilot_api.client import (
    JobPilotApiError,
    create_job,
    get_base_resume,
    get_description,
    get_description_for_job,
    get_job,
    get_match,
    get_profile,
    link_description,
    list_raw_descriptions,
    set_description_status,
    set_token,
    store_resume,
    update_description,
    write_match,
)

NAME = "jobpilot_api"

__all__ = [
    "NAME",
    "JobPilotApiError",
    "create_job",
    "get_base_resume",
    "get_description",
    "get_description_for_job",
    "get_job",
    "get_match",
    "get_profile",
    "link_description",
    "list_raw_descriptions",
    "set_description_status",
    "set_token",
    "store_resume",
    "update_description",
    "write_match",
]
