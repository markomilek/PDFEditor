"""Skeleton tests for future page-removal rewrite behavior."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from pdfeditor.models import RunConfig
from pdfeditor.processor import process_pdf
from pdfeditor.rewrite import rewrite_pdf_removing_pages
from tests.pdf_factory import empty_page, text_page, write_pdf_with_pages


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


def test_process_pdf_uses_numeric_suffix_when_output_exists(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    report_dir = tmp_path / "reports"
    input_dir.mkdir()
    out_dir.mkdir()

    input_path = write_pdf_with_pages(
        input_dir / "sample.pdf",
        page_specs=[text_page("cover"), empty_page(), text_page("appendix")],
    )
    write_pdf_with_pages(
        out_dir / "sample.edited.pdf",
        page_specs=[text_page("existing")],
    )

    config = RunConfig(
        path=str(input_dir),
        out=str(out_dir),
        report_dir=str(report_dir),
        mode="structural",
        effective_mode="structural",
        render_dpi=72,
        ink_threshold=0.0005,
        background="white",
        effective_background="white",
        render_sample="all",
        white_threshold=250,
        center_margin=0.05,
        recursive=False,
        write_when_unchanged=False,
        treat_annotations_as_empty=True,
        dry_run=False,
        debug_structural=False,
        debug_pypdf_xref=False,
        strict_xref=False,
        debug_render=False,
        verbose=False,
    )

    result = process_pdf(input_path=input_path, out_dir=out_dir, config=config)

    assert result.status == "edited"
    assert result.output_path is not None
    assert result.output_path.endswith("sample.edited.1.pdf")
    assert any("already existed" in warning for warning in result.warnings)
