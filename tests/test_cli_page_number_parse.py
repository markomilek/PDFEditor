"""CLI parsing tests for page-number stamping options."""

from __future__ import annotations

from pathlib import Path

import pytest

from pdfeditor.cli import build_parser, run_cli


def test_stamp_page_numbers_requires_pagenum_box(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    report_dir = tmp_path / "reports"
    input_dir.mkdir()

    with pytest.raises(SystemExit) as exc_info:
        run_cli(
            [
                "--path",
                str(input_dir),
                "--report-dir",
                str(report_dir),
                "--stamp-page-numbers",
            ]
        )

    assert exc_info.value.code == 2


def test_stamp_page_numbers_force_requires_stamping(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    report_dir = tmp_path / "reports"
    input_dir.mkdir()

    with pytest.raises(SystemExit) as exc_info:
        run_cli(
            [
                "--path",
                str(input_dir),
                "--report-dir",
                str(report_dir),
                "--stamp-page-numbers-force",
            ]
        )

    assert exc_info.value.code == 2


def test_stamp_page_numbers_force_with_stamping_parses_ok() -> None:
    args = build_parser().parse_args(
        [
            "--stamp-page-numbers",
            "--stamp-page-numbers-force",
            "--pagenum-box",
            "1, 0.5, 2, 0.25",
        ]
    )
    assert args.stamp_page_numbers is True
    assert args.stamp_page_numbers_force is True
    assert args.pagenum_box == (1.0, 0.5, 2.0, 0.25)


def test_pagenum_box_parses_valid_tuple() -> None:
    args = build_parser().parse_args(["--pagenum-box", "1, 0.5, 2, 0.25"])
    assert args.pagenum_box == (1.0, 0.5, 2.0, 0.25)


def test_pagenum_box_rejects_invalid_format() -> None:
    with pytest.raises(SystemExit) as exc_info:
        build_parser().parse_args(["--pagenum-box", "1,0,0"])
    assert exc_info.value.code == 2


def test_pagenum_box_rejects_negative_values() -> None:
    with pytest.raises(SystemExit) as exc_info:
        build_parser().parse_args(["--pagenum-box", "1,-0.5,2,0.25"])
    assert exc_info.value.code == 2
