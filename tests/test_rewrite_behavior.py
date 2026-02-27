"""Skeleton tests for future page-removal rewrite behavior."""

from __future__ import annotations

from pathlib import Path

import pytest
from pypdf import PdfReader

from pdfeditor.rewrite import rewrite_pdf_removing_pages
from tests.pdf_factory import empty_page, text_page, write_pdf_with_pages


@pytest.mark.xfail(
    reason="Rewrite logic not implemented yet",
    raises=NotImplementedError,
    strict=True,
)
def test_rewrite_removes_empty_middle_page_and_uses_suffix(tmp_path: Path) -> None:
    input_path = write_pdf_with_pages(
        tmp_path / "sample.pdf",
        page_specs=[text_page("cover"), empty_page(), text_page("appendix")],
    )
    output_path = tmp_path / "sample.edited.pdf"

    rewrite_pdf_removing_pages(
        input_path=input_path,
        output_path=output_path,
        pages_to_remove={1},
    )

    assert output_path.name.endswith(".edited.pdf")
    reader = PdfReader(output_path)
    assert len(reader.pages) == 2
