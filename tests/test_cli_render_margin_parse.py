"""CLI tests for render sample margin parsing."""

from __future__ import annotations

import pytest

from pdfeditor.cli import build_parser


def test_render_sample_margin_parses_zero_margins() -> None:
    args = build_parser().parse_args(["--render-sample-margin", "0,0,0,0"])
    assert args.render_sample_margin == (0.0, 0.0, 0.0, 0.0)


def test_render_sample_margin_parses_spaces_and_decimals() -> None:
    args = build_parser().parse_args(["--render-sample-margin", "0.5, 0, 0, 1.25"])
    assert args.render_sample_margin == (0.5, 0.0, 0.0, 1.25)


def test_render_sample_margin_rejects_wrong_count() -> None:
    with pytest.raises(SystemExit) as exc_info:
        build_parser().parse_args(["--render-sample-margin", "0,0,0"])
    assert exc_info.value.code == 2


def test_render_sample_margin_rejects_negative_values() -> None:
    with pytest.raises(SystemExit) as exc_info:
        build_parser().parse_args(["--render-sample-margin", "0,-1,0,0"])
    assert exc_info.value.code == 2
