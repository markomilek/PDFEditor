"""Placeholder APIs for PDF rewrite behavior."""

from __future__ import annotations

from collections.abc import Collection
from pathlib import Path


def rewrite_pdf_removing_pages(
    input_path: Path,
    output_path: Path,
    pages_to_remove: Collection[int],
) -> Path:
    """Rewrite a PDF while removing the specified zero-based page indexes."""
    raise NotImplementedError("PDF rewrite is not implemented yet.")
