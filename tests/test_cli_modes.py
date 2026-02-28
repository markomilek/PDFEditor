"""CLI tests for render mode configuration and fallback behavior."""

from __future__ import annotations

import json
from pathlib import Path

from pdfeditor.cli import build_parser, run_cli
from tests.pdf_factory import empty_page, text_page, write_pdf_with_pages


def test_cli_parses_render_mode_arguments() -> None:
    args = build_parser().parse_args(
        [
            "--mode",
            "render",
            "--render-dpi",
            "96",
            "--ink-threshold",
            "0.01",
            "--background",
            "auto",
            "--render-sample",
            "center",
        ]
    )

    assert args.mode == "render"
    assert args.render_dpi == 96
    assert args.ink_threshold == 0.01
    assert args.background == "auto"
    assert args.render_sample == "center"


def test_cli_both_mode_falls_back_to_structural_when_render_backend_missing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    report_dir = tmp_path / "reports"
    input_dir.mkdir()

    write_pdf_with_pages(
        input_dir / "sample.pdf",
        page_specs=[text_page("cover"), empty_page(), text_page("appendix")],
    )

    monkeypatch.setattr("pdfeditor.cli.is_render_backend_available", lambda: False)

    exit_code = run_cli(
        [
            "--mode",
            "both",
            "--path",
            str(input_dir),
            "--out",
            str(output_dir),
            "--report-dir",
            str(report_dir),
        ]
    )

    assert exit_code == 0
    assert sorted(path.name for path in output_dir.glob("*.pdf")) == ["sample.edited.pdf"]

    payload = json.loads(next(report_dir.glob("run_report_*.json")).read_text(encoding="utf-8"))
    assert payload["config"]["mode"] == "both"
    assert payload["config"]["effective_mode"] == "structural"
    assert payload["warnings"]


def test_cli_render_mode_fails_when_render_backend_missing(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    input_dir = tmp_path / "input"
    report_dir = tmp_path / "reports"
    input_dir.mkdir()

    monkeypatch.setattr("pdfeditor.cli.is_render_backend_available", lambda: False)

    exit_code = run_cli(
        [
            "--mode",
            "render",
            "--path",
            str(input_dir),
            "--report-dir",
            str(report_dir),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "requires optional dependency 'pypdfium2'" in captured.out
    payload = json.loads(next(report_dir.glob("run_report_*.json")).read_text(encoding="utf-8"))
    assert payload["errors"]
