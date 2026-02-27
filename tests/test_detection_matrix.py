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
    footer_page_number_page,
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
