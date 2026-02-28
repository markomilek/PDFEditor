"""End-to-end CLI tests for PDFEditor."""

from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader
import pytest

from pdfeditor.cli import run_cli
from tests.pdf_factory import empty_page, text_page, write_pdf_with_pages


def test_cli_processes_pdfs_and_writes_reports(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    report_dir = tmp_path / "reports"
    input_dir.mkdir()

    write_pdf_with_pages(
        input_dir / "sample.pdf",
        page_specs=[text_page("cover"), empty_page(), text_page("appendix")],
    )

    exit_code = run_cli(
        [
            "--path",
            str(input_dir),
            "--out",
            str(output_dir),
            "--report-dir",
            str(report_dir),
        ]
    )

    assert exit_code == 0

    output_files = sorted(output_dir.glob("*.pdf"))
    assert [path.name for path in output_files] == ["sample.edited.pdf"]
    output_reader = PdfReader(output_files[0])
    assert len(output_reader.pages) == 2

    json_reports = sorted(report_dir.glob("run_report_*.json"))
    txt_reports = sorted(report_dir.glob("run_report_*.txt"))
    assert len(json_reports) == 1
    assert len(txt_reports) == 1

    payload = json.loads(json_reports[0].read_text(encoding="utf-8"))
    assert payload["totals"]["files_found"] == 1
    assert payload["totals"]["pages_removed_total"] == 1
    assert payload["files"][0]["status"] == "edited"
    assert "pypdfium2_version" in payload


@pytest.mark.parametrize(
    ("margin", "expected_removed"),
    [("0,0,0,1", 1), ("0,0,0,2", 2)],
)
def test_cli_render_sample_margin_changes_uat_simple_page_removal(
    tmp_path: Path,
    margin: str,
    expected_removed: int,
) -> None:
    pytest.importorskip(
        "pypdfium2",
        reason="UAT render sample margin regression test requires pypdfium2.",
    )

    project_root = Path(__file__).resolve().parents[1]
    input_dir = project_root / "uat" / "input"
    target_input = input_dir / "Corporate_UAT_Simple.pdf"
    output_dir = tmp_path / f"output_{margin.replace(',', '_')}"
    report_dir = tmp_path / f"reports_{margin.replace(',', '_')}"
    expected_output = output_dir / "Corporate_UAT_Simple.edited.pdf"

    exit_code = run_cli(
        [
            "--verbose",
            "--path",
            str(input_dir),
            "--out",
            str(output_dir),
            "--report-dir",
            str(report_dir),
            "--render-sample-margin",
            margin,
        ]
    )

    assert exit_code == 2
    assert expected_output.exists()

    report_path = next(report_dir.glob("run_report_*.json"))
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    file_result = next(
        file
        for file in payload["files"]
        if file["input_path"] == str(target_input)
    )

    assert file_result["status"] == "edited"
    assert file_result["output_path"] == str(expected_output)
    assert file_result["pages_removed"] == expected_removed
