"""Tests for structural debug artifact generation."""

from __future__ import annotations

import json
from pathlib import Path

from pdfeditor.models import RunConfig
from pdfeditor.processor import process_pdf
from tests.pdf_factory import empty_page, text_page, write_pdf_with_pages


def test_process_pdf_writes_structural_debug_artifact(tmp_path: Path) -> None:
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
        mode="structural",
        effective_mode="structural",
        render_dpi=72,
        ink_threshold=0.0005,
        background="white",
        effective_background="white",
        render_sample="all",
        recursive=False,
        write_when_unchanged=False,
        treat_annotations_as_empty=True,
        dry_run=False,
        debug_structural=True,
        verbose=False,
    )

    result = process_pdf(input_path=input_path, out_dir=out_dir, config=config)

    assert result.structural_debug_path is not None
    debug_path = Path(result.structural_debug_path)
    assert debug_path.exists()

    payload = json.loads(debug_path.read_text(encoding="utf-8"))
    assert payload["input_path"] == str(input_path)
    assert isinstance(payload["pages"], list)
    assert len(payload["pages"]) == 2

    first_page = payload["pages"][0]
    assert {
        "page_index_0",
        "page_index_1",
        "media_box",
        "crop_box",
        "has_contents",
        "contents_object_type",
        "number_of_content_streams",
        "total_contents_bytes",
        "resources_keys_present",
        "annotations_count",
        "operator_summary",
    }.issubset(first_page)

    operator_summary = first_page["operator_summary"]
    assert {
        "total_operations_count",
        "unique_operators_count",
        "top_operators_by_frequency",
        "paint_ops_seen",
        "text_show_ops_seen",
        "xobject_paint_seen",
        "tr_events",
        "tf_events",
        "gs_events",
        "parsing_exceptions",
    }.issubset(operator_summary)
