"""Safe logging. Records carry method, matched route path, status, duration and a server-generated request id only.

Request bodies, query strings, headers, response bodies and exception messages are never logged, because any of them
can contain financial data. Unhandled errors log the exception TYPE only.
"""

from __future__ import annotations

import logging

LOGGER_NAME = "finguard_server"


def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


def configure_logging(level: str) -> None:
    logger = get_logger()
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        logger.addHandler(handler)
    logger.propagate = False
