"""Regression tests for invisible paint handling in structural detection."""

from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader

from pdfeditor.detect_empty import detect_page_decisions
from tests.pdf_factory import (
    create_pdf_with_pages,
    invisible_text_opacity_zero_page,
    invisible_text_tr3_page,
    invisible_text_zero_font_size_page,
    text_page,
)


def test_invisible_paint_pages_are_empty_but_visible_text_is_not() -> None:
    pdf_bytes = create_pdf_with_pages(
        [
            invisible_text_tr3_page(),
            invisible_text_zero_font_size_page(),
            invisible_text_opacity_zero_page(),
            text_page("Visible control"),
        ]
    )
    reader = PdfReader(BytesIO(pdf_bytes))

    decisions = detect_page_decisions(reader, treat_annotations_as_empty=True)

    assert len(decisions) == 4
    assert decisions[0].is_empty is True
    assert decisions[0].reason == "only_invisible_paint"
    assert decisions[1].is_empty is True
    assert decisions[1].reason == "only_invisible_paint"
    assert decisions[2].is_empty is True
    assert decisions[2].reason == "only_invisible_paint"
    assert decisions[3].is_empty is False
    assert decisions[3].reason == "visible_text"
