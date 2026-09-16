import logging
import re
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

REDACTED = "[redacted]"

_SENSITIVE_KEY = re.compile(
    r"(api[_-]?key|secret|token|password|passwd|credential|connection[_-]?string|dsn|sas)",
    re.IGNORECASE,
)


def redact_sensitive(
    _logger: Any,
    _method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Mask values whose key looks like a credential.

    Redaction happens in the logging pipeline rather than at each call site
    because call sites are where mistakes are made. A field added in six months
    is covered without anyone remembering this rule exists.
    """
    return _redact_mapping(event_dict)


def _redact_mapping(mapping: EventDict) -> EventDict:
    redacted: EventDict = {}
    for key, value in mapping.items():
        if isinstance(key, str) and _SENSITIVE_KEY.search(key):
            redacted[key] = REDACTED
        elif isinstance(value, dict):
            redacted[key] = _redact_mapping(value)
        else:
            redacted[key] = value
    return redacted


def configure_logging(level: str = "INFO", *, environment: str = "local") -> None:
    """Emit structured JSON on stdout.

    Container Apps forwards stdout to Log Analytics, which parses JSON into
    queryable columns. Human-readable formatting would have to be undone there,
    so the same format is used locally to keep the two environments comparable.
    """
    shared: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        redact_sensitive,
    ]

    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)

    structlog.configure(
        processors=[
            *shared,
            structlog.processors.EventRenamer("message"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelNamesMapping()[level]),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    structlog.contextvars.bind_contextvars(environment=environment)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger
