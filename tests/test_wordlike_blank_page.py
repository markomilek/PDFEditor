"""Regression test for blank pages that carry font resources."""

from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader

from pdfeditor.detect_empty import detect_page_decisions
from tests.pdf_factory import create_wordlike_blank_then_text_pdf


def test_wordlike_blank_page_with_copied_fonts_is_still_empty() -> None:
    pdf_bytes = create_wordlike_blank_then_text_pdf("Visible page 2 text")
    reader = PdfReader(BytesIO(pdf_bytes))

    decisions = detect_page_decisions(reader, treat_annotations_as_empty=True)

    assert len(decisions) == 2
    assert decisions[0].is_empty is True
    assert decisions[0].reason in {"no_paint_ops", "contents_whitespace_only", "no_contents"}
    assert decisions[0].details["fonts_present"] is True
    assert decisions[0].details["paint_ops_found"] == []
    assert decisions[0].details["state_ops_found"] != []
    assert decisions[1].is_empty is False
