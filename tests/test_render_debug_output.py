"""Tests for render debug artifact generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("pypdfium2", reason="Optional render debug requires pypdfium2")

from pdfeditor.models import RunConfig
from pdfeditor.processor import process_pdf
from tests.pdf_factory import empty_page, text_page, write_pdf_with_pages


def test_process_pdf_writes_render_debug_artifact(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    report_dir = tmp_path / "reports"
    input_dir.mkdir()

    input_path = write_pdf_with_pages(
        input_dir / "sample.pdf",
        page_specs=[empty_page(), text_page("Visible text")],
    )

    config = RunConfig(
        path=str(input_dir),
        out=str(out_dir),
        report_dir=str(report_dir),
        mode="render",
        effective_mode="render",
        render_dpi=72,
        ink_threshold=0.0005,
        background="white",
        effective_background="white",
        render_sample_margin=(0.25, 0.25, 0.25, 0.25),
        white_threshold=250,
        stamp_page_numbers=False,
        stamp_page_numbers_force=False,
        pagenum_box=None,
        pagenum_size=10.0,
        pagenum_font="Helvetica",
        pagenum_format="{page}",
        recursive=False,
        write_when_unchanged=False,
        treat_annotations_as_empty=True,
        dry_run=False,
        debug_structural=False,
        debug_pypdf_xref=False,
        strict_xref=False,
        debug_render=True,
        verbose=False,
    )

    result = process_pdf(input_path=input_path, out_dir=out_dir, config=config)

    assert result.render_debug_path is not None
    debug_path = Path(result.render_debug_path)
    assert debug_path.exists()

    payload = json.loads(debug_path.read_text(encoding="utf-8"))
    assert payload["render_parameters"]["white_threshold"] == 250
    assert payload["render_parameters"]["render_sample_margin"] == [0.25, 0.25, 0.25, 0.25]
    assert len(payload["per_page"]) == 2
    assert payload["per_page"][0]["sample_margin_inches"] == [0.25, 0.25, 0.25, 0.25]
    assert "sample_box_px" in payload["per_page"][0]
    assert payload["per_page"][0]["ink_ratio"] <= payload["per_page"][1]["ink_ratio"]
