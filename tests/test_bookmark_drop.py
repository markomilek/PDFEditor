"""Skeleton tests for future bookmark-drop rewrite behavior."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from pdfeditor.rewrite import rewrite_pdf_removing_pages
from tests.pdf_factory import OutlineSpec, empty_page, text_page, write_pdf_with_pages


def test_bookmark_referencing_removed_page_is_dropped(tmp_path: Path) -> None:
    input_path = write_pdf_with_pages(
        tmp_path / "bookmark-source.pdf",
        page_specs=[text_page("front"), empty_page(), text_page("back")],
        outline_specs=[OutlineSpec(title="Empty Page Bookmark", page_index=1)],
    )
    output_path = tmp_path / "bookmark-source.edited.pdf"

    rewrite_pdf_removing_pages(
        input_path=input_path,
        output_path=output_path,
        pages_to_remove={1},
    )

    reader = PdfReader(output_path)
    assert len(reader.pages) == 2
    assert reader.outline == []
