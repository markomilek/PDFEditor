"""Placeholder APIs for empty-page detection."""

from __future__ import annotations

from collections.abc import Sequence


def detect_empty_pages(pdf_bytes: bytes) -> Sequence[bool]:
    """Return per-page empty-page decisions for a PDF payload."""
    raise NotImplementedError("Empty-page detection is not implemented yet.")
