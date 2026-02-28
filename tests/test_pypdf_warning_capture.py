"""Tests for pypdf warning capture and strict handling."""

from __future__ import annotations

import logging

import pytest

from pdfeditor.pypdf_debug import (
    PyPdfWarningCollector,
    capture_pypdf_warnings,
    ensure_no_pypdf_warnings,
)


def test_capture_pypdf_warnings_collects_message_and_stack() -> None:
    collector = PyPdfWarningCollector()

    with capture_pypdf_warnings(collector):
        logging.getLogger("pypdf").warning("Ignoring wrong pointing object 1 0 (offset 0)")

    assert len(collector.events) == 1
    event = collector.events[0]
    assert event.message == "Ignoring wrong pointing object 1 0 (offset 0)"
    assert event.logger_name == "pypdf"
    assert event.stack


def test_ensure_no_pypdf_warnings_raises_in_strict_mode() -> None:
    collector = PyPdfWarningCollector()
    with capture_pypdf_warnings(collector):
        logging.getLogger("pypdf").warning("Ignoring wrong pointing object 1 0 (offset 0)")

    with pytest.raises(ValueError, match="pypdf_xref_warning"):
        ensure_no_pypdf_warnings(collector)
