"""End-to-end CLI tests for PDFEditor."""

from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader

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
