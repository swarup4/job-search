"""Uvicorn configures only its own loggers. Without this, every record the
application writes — the middleware's included — reaches no handler and is
discarded."""

import logging
import os

from config.error_log import ErrorLogHandler


def configure_logging() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )
    # basicConfig is a no-op once the root has a handler; this has to be made one.
    root = logging.getLogger()
    if not any(isinstance(handler, ErrorLogHandler) for handler in root.handlers):
        root.addHandler(ErrorLogHandler("server"))
