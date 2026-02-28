"""pypdf warning capture helpers for deterministic debugging artifacts."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import logging
import traceback
from typing import Iterator


@dataclass(frozen=True)
class PyPdfWarningEvent:
    """Structured capture of one pypdf warning log event."""

    level: str
    message: str
    logger_name: str
    timestamp_utc: str
    stack: list[str]
    extra: dict[str, str | int | None] = field(default_factory=dict)


@dataclass
class PyPdfWarningCollector:
    """In-memory collector for pypdf warning events."""

    events: list[PyPdfWarningEvent] = field(default_factory=list)

    def add_from_log_record(self, record: logging.LogRecord) -> None:
        """Convert and store one log record from the pypdf logger."""
        stack_lines = traceback.format_stack(limit=25)
        self.events.append(
            PyPdfWarningEvent(
                level=record.levelname,
                message=record.getMessage(),
                logger_name=record.name,
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
                stack=[line.rstrip("\n") for line in stack_lines],
                extra={
                    "pathname": record.pathname,
                    "lineno": record.lineno,
                    "funcName": record.funcName,
                },
            )
        )

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation of the collector."""
        return {
            "warnings_count": len(self.events),
            "events": [asdict(event) for event in self.events],
        }


class _CollectorHandler(logging.Handler):
    """Logging handler that stores WARNING+ events into a collector."""

    def __init__(self, collector: PyPdfWarningCollector) -> None:
        super().__init__(level=logging.WARNING)
        self.collector = collector

    def emit(self, record: logging.LogRecord) -> None:
        """Capture the warning event without re-printing it."""
        if record.levelno < logging.WARNING:
            return
        self.collector.add_from_log_record(record)


@contextmanager
def capture_pypdf_warnings(collector: PyPdfWarningCollector) -> Iterator[None]:
    """Capture pypdf warnings into a collector without console spam."""
    logger = logging.getLogger("pypdf")
    handler = _CollectorHandler(collector)
    previous_level = logger.level
    previous_propagate = logger.propagate
    logger.addHandler(handler)
    logger.setLevel(logging.WARNING)
    logger.propagate = False
    try:
        yield
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)
        logger.propagate = previous_propagate


def ensure_no_pypdf_warnings(collector: PyPdfWarningCollector) -> None:
    """Raise when strict xref mode forbids captured pypdf warnings."""
    if collector.events:
        raise ValueError("pypdf_xref_warning")
