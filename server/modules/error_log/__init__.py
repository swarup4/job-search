"""Public interface of the error log module — the dashboard's view of the shared error
file, and the way the browser adds its own failures to it. It owns no collection."""

from modules.error_log.router import router

NAME = "errorLog"

__all__ = ["NAME", "router"]
