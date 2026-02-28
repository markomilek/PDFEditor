"""Skeleton tests for future empty-page detection behavior."""

from __future__ import annotations

from io import BytesIO

import pytest
from pypdf import PdfReader

pypdf = pytest.importorskip("pypdf", reason="pypdf is required for PDF factory tests")

from pdfeditor.detect_empty import detect_empty_pages, is_page_empty_structural
from tests.pdf_factory import (
    annotation_only_page,
    create_pdf_with_pages,
    empty_page,
    font_resources_only_page,
    footer_page_number_page,
    invisible_text_tr3_page,
    state_ops_only_page,
    text_page,
    whitespace_only_page,
)


@pytest.mark.parametrize(
    ("label", "page_specs", "expected"),
    [
        pytest.param(
            "structural-empty-page",
            [empty_page()],
            [True],
            id="structural-empty-page",
        ),
        pytest.param(
            "annotation-only-page",
            [annotation_only_page()],
            [True],
            id="annotation-only-page",
        ),
        pytest.param(
            "blank-page-with-fonts-in-resources-no-ops",
            [font_resources_only_page()],
            [True],
            id="blank-page-with-fonts-in-resources-no-ops",
        ),
        pytest.param(
            "state-ops-only-page",
            [state_ops_only_page()],
            [True],
            id="state-ops-only-page",
        ),
        pytest.param(
            "invisible-text-tr3-page",
            [invisible_text_tr3_page()],
            [True],
            id="invisible-text-tr3-page",
        ),
        pytest.param(
            "page-number-text-page",
            [text_page("1")],
            [False],
            id="page-number-text-page",
        ),
        pytest.param(
            "footer-page-number-text-page",
            [footer_page_number_page("Page 3")],
            [False],
            id="footer-page-number-text-page",
        ),
        pytest.param(
            "whitespace-only-content-page",
            [whitespace_only_page()],
            [True],
            id="whitespace-only-content-page",
        ),
    ],
)
def test_detection_matrix_future_behavior(
    label: str,
    page_specs: list[object],
    expected: list[bool],
) -> None:
    del label
    pdf_bytes = create_pdf_with_pages(page_specs)
    result = detect_empty_pages(pdf_bytes)
    assert list(result) == expected


def test_annotation_only_page_is_not_empty_when_annotations_are_not_treated_as_empty() -> None:
    pdf_bytes = create_pdf_with_pages([annotation_only_page()])
    reader = PdfReader(BytesIO(pdf_bytes))
    is_empty, _, _ = is_page_empty_structural(
        reader.pages[0],
        treat_annotations_as_empty=False,
    )
    assert is_empty is False


def test_blank_page_with_fonts_in_resources_records_fonts_but_is_empty() -> None:
    pdf_bytes = create_pdf_with_pages([font_resources_only_page()])
    reader = PdfReader(BytesIO(pdf_bytes))
    is_empty, reason, details = is_page_empty_structural(
        reader.pages[0],
        treat_annotations_as_empty=True,
    )
    assert is_empty is True
    assert reason in {"no_contents", "no_paint_ops", "contents_whitespace_only"}
    assert details["fonts_present"] is True
    assert details["paint_ops_found"] == []


def test_state_ops_only_page_is_empty_and_records_state_ops() -> None:
    pdf_bytes = create_pdf_with_pages([state_ops_only_page()])
    reader = PdfReader(BytesIO(pdf_bytes))
    is_empty, reason, details = is_page_empty_structural(
        reader.pages[0],
        treat_annotations_as_empty=True,
    )
    assert is_empty is True
    assert reason == "no_paint_ops"
    assert details["paint_ops_found"] == []
    assert details["state_ops_found"] != []


def test_invisible_text_tr3_page_is_empty_and_recorded_as_invisible_paint() -> None:
    pdf_bytes = create_pdf_with_pages([invisible_text_tr3_page()])
    reader = PdfReader(BytesIO(pdf_bytes))
    is_empty, reason, details = is_page_empty_structural(
        reader.pages[0],
        treat_annotations_as_empty=True,
    )
    assert is_empty is True
    assert reason == "only_invisible_paint"
    assert details["invisible_text_events_count"] == 1
    assert details["last_seen_Tr"] == 3
