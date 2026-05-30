"""JSON-structured session logger for RedTeamAgentLoop.

Each session writes to ``<log_dir>/{session_id}.log``.
Every log record is a single JSON object on one line (NDJSON format), so logs
can be parsed with ``jq`` or streamed into any log aggregator.

Log level and directory are set once at startup via ``configure_logging()``,
which reads ``REDTEAM_LOG_LEVEL`` / ``REDTEAM_LOG_DIR`` env vars as fallbacks.
All subsequent ``get_session_logger()`` calls inherit that configuration.

Usage::

    # In main() — call once before any node runs:
    configure_logging(log_level="INFO", log_dir="reports/logs")

    # In nodes:
    log = get_session_logger(session_id)
    log.debug("node started", extra={"node": "attacker", "iteration": 3, "session_id": session_id})
    log.error("LLM call failed", exc_info=True, extra={"node": "target_caller", "session_id": session_id})

    # To print the log path at startup:
    print(get_log_path(session_id))
"""

from __future__ import annotations

import json
import logging
import os
import traceback
from pathlib import Path


# ---------------------------------------------------------------------------
# JSON formatter
# ---------------------------------------------------------------------------

class _JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON objects (NDJSON)."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "timestamp": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        for field in ("node", "iteration", "session_id"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        if record.exc_info:
            payload["traceback"] = traceback.format_exception(*record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Module-level configuration (set once by configure_logging, read by all loggers)
# ---------------------------------------------------------------------------

_log_level: int = logging.DEBUG
_log_dir: str = "reports/logs"


def configure_logging(log_level: str = "DEBUG", log_dir: str = "reports/logs") -> None:
    """Set the log level and directory for all session loggers.

    Call this once from ``main()`` before any session logger is created.
    If not called, defaults to DEBUG level and ``reports/logs/``.

    ``REDTEAM_LOG_LEVEL`` and ``REDTEAM_LOG_DIR`` env vars are used as
    fallbacks when the caller does not pass explicit values.
    """
    global _log_level, _log_dir
    effective_level = os.environ.get("REDTEAM_LOG_LEVEL", log_level).upper()
    effective_dir = os.environ.get("REDTEAM_LOG_DIR", log_dir)
    _log_level = getattr(logging, effective_level, logging.DEBUG)
    _log_dir = effective_dir


def get_log_path(session_id: str) -> str:
    """Return the absolute path of the log file for *session_id*."""
    return str(Path(_log_dir).resolve() / f"{session_id}.log")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_session_logger(session_id: str) -> logging.Logger:
    """Return a logger that writes JSON to ``<log_dir>/{session_id}.log``.

    Calling this multiple times with the same *session_id* returns the same
    logger instance without adding duplicate handlers.
    """
    Path(_log_dir).mkdir(parents=True, exist_ok=True)
    log_path = Path(_log_dir) / f"{session_id}.log"

    logger_name = f"redteam.{session_id}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(_log_level)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
        handler.setFormatter(_JsonFormatter())
        logger.addHandler(handler)

    return logger
