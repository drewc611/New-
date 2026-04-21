"""Structured JSON logging with PII redaction."""
from __future__ import annotations

import logging
import sys

import structlog

PII_FIELDS = {"address", "street", "email", "phone", "ssn", "password", "api_key"}


def _redact_pii(logger, method_name, event_dict):
    for key in list(event_dict.keys()):
        if key.lower() in PII_FIELDS:
            event_dict[key] = "[REDACTED]"
    return event_dict


def configure_logging(level: str = "INFO") -> None:
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=log_level)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _redact_pii,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    return structlog.get_logger(name) if name else structlog.get_logger()
