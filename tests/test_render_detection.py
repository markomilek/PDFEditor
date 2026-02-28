"""Optional render-based detection tests."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("pypdfium2", reason="Optional render detector requires pypdfium2")

from pdfeditor.detect_render import detect_empty_pages_render
from tests.pdf_factory import empty_page, text_page, write_pdf_with_pages


def test_render_detector_flags_blank_page_and_visible_text(tmp_path: Path) -> None:
    pdf_path = write_pdf_with_pages(
        tmp_path / "render-sample.pdf",
        page_specs=[empty_page(), text_page("Visible text")],
    )

    decisions = detect_empty_pages_render(
        input_path=pdf_path,
        dpi=72,
        ink_threshold=0.0005,
        sample="all",
        background="white",
    )

    assert len(decisions) == 2
    assert decisions[0].is_empty is True
    assert decisions[0].reason == "ink_below_threshold"
    assert decisions[1].is_empty is False
    assert decisions[1].reason == "ink_above_threshold"
