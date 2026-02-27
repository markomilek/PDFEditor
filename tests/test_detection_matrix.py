"""Skeleton tests for future empty-page detection behavior."""

from __future__ import annotations

import pytest

pypdf = pytest.importorskip("pypdf", reason="pypdf is required for PDF factory tests")

from pdfeditor.detect_empty import detect_empty_pages
from tests.pdf_factory import (
    annotation_only_page,
    create_pdf_with_pages,
    empty_page,
    footer_page_number_page,
    text_page,
    whitespace_only_page,
)


@pytest.mark.xfail(
    reason="Empty-page detection not implemented yet",
    raises=NotImplementedError,
    strict=True,
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
