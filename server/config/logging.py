"""Uvicorn configures only its own loggers. Without this, every record the
application writes — the middleware's included — reaches no handler and is
discarded."""

import logging
import os


def configure_logging() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )
