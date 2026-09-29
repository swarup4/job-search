"""Public interface of the status module: every number the dashboard shows outside a
page's own list — badges, pipeline totals, job counts, the last discovery, the profile
index — in one read. It owns no collection; it asks the modules that do."""

from modules.status.router import router

NAME = "status"

__all__ = ["NAME", "router"]
