"""Tests for page-number stamping behavior and formatting."""

from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path

from pypdf import PageObject, PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
import pytest

from pdfeditor.cli import run_cli
from pdfeditor.stamp_page_numbers import format_page_label, to_roman

PAGE_WIDTH = 612
PAGE_HEIGHT = 792
STAMP_BOX_IN = (0.75, 0.25, 1.0, 0.5)


def test_to_roman_basic_cases() -> None:
    assert to_roman(1) == "I"
    assert to_roman(4) == "IV"
    assert to_roman(9) == "IX"
    assert to_roman(58) == "LVIII"
    assert to_roman(1994) == "MCMXCIV"


def test_format_page_label_supports_tokens() -> None:
    assert format_page_label(3, "{page}") == "3"
    assert format_page_label(4, "{roman}") == "iv"
    assert format_page_label(9, "{ROMAN}") == "IX"
    assert format_page_label(12, "Page {page}") == "Page 12"
    assert format_page_label(7, "literal") == "literal"


def test_page_number_stamping_adds_footer_ink(tmp_path: Path) -> None:
    pytest.importorskip("pypdfium2", reason="Stamping test requires pypdfium2.")

    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    report_dir = tmp_path / "reports"
    input_dir.mkdir()

    pdf_path = input_dir / "stamp.pdf"
    _write_test_pdf(
        pdf_path,
        page_contents=(
            None,
            None,
            "BT /F1 24 Tf 72 700 Td (Body content) Tj ET",
        ),
    )

    exit_code = run_cli(
        [
            "--mode",
            "structural",
            "--path",
            str(input_dir),
            "--out",
            str(output_dir),
            "--report-dir",
            str(report_dir),
            "--stamp-page-numbers",
            "--pagenum-box",
            _format_box(STAMP_BOX_IN),
        ]
    )

    assert exit_code == 0
    output_path = output_dir / "stamp.edited.pdf"
    assert output_path.exists()
    assert len(PdfReader(output_path).pages) == 1

    xs = _nonwhite_x_positions(pdf_path=output_path, box_in=STAMP_BOX_IN, dpi=144)
    assert xs
    width_px = int(round(STAMP_BOX_IN[2] * 144))
    center_px = width_px / 2.0
    centroid_px = sum(xs) / len(xs)
    assert abs(centroid_px - center_px) <= width_px * 0.25


def test_page_number_stamping_guardrail_skips_when_box_has_real_content(tmp_path: Path) -> None:
    pytest.importorskip("pypdfium2", reason="Stamping test requires pypdfium2.")

    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    report_dir = tmp_path / "reports"
    input_dir.mkdir()

    pdf_path = input_dir / "guardrail.pdf"
    _write_test_pdf(
        pdf_path,
        page_contents=(
            None,
            None,
            "BT /F1 24 Tf 72 700 Td (Body content) Tj ET BT /F1 24 Tf 72 36 Td (3) Tj ET",
        ),
    )

    exit_code = run_cli(
        [
            "--mode",
            "structural",
            "--path",
            str(input_dir),
            "--out",
            str(output_dir),
            "--report-dir",
            str(report_dir),
            "--debug-render",
            "--stamp-page-numbers",
            "--pagenum-box",
            _format_box(STAMP_BOX_IN),
        ]
    )

    assert exit_code == 0
    stamp_debug_path = next(report_dir.glob("stamp_debug_*.json"))
    payload = json.loads(stamp_debug_path.read_text(encoding="utf-8"))
    assert payload["per_page"][0]["action"] == "skipped_guardrail"
    assert payload["per_page"][0]["forced"] is False


def test_page_number_stamping_force_bypasses_guardrail(tmp_path: Path) -> None:
    pytest.importorskip("pypdfium2", reason="Stamping test requires pypdfium2.")

    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    report_dir = tmp_path / "reports"
    input_dir.mkdir()

    pdf_path = input_dir / "forced.pdf"
    _write_test_pdf(
        pdf_path,
        page_contents=(
            None,
            None,
            "BT /F1 24 Tf 72 700 Td (Body content) Tj ET BT /F1 24 Tf 72 36 Td (3) Tj ET",
        ),
    )

    exit_code = run_cli(
        [
            "--mode",
            "structural",
            "--path",
            str(input_dir),
            "--out",
            str(output_dir),
            "--report-dir",
            str(report_dir),
            "--debug-render",
            "--stamp-page-numbers",
            "--stamp-page-numbers-force",
            "--pagenum-box",
            _format_box(STAMP_BOX_IN),
        ]
    )

    assert exit_code == 0
    stamp_debug_path = next(report_dir.glob("stamp_debug_*.json"))
    payload = json.loads(stamp_debug_path.read_text(encoding="utf-8"))
    assert payload["per_page"][0]["action"] == "stamped_forced"
    assert payload["per_page"][0]["forced"] is True


def _write_test_pdf(destination: Path, page_contents: tuple[str | None, ...]) -> None:
    writer = PdfWriter()
    for content in page_contents:
        page = PageObject.create_blank_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        if content is not None:
            page[NameObject("/Resources")] = _font_resources()
            stream = DecodedStreamObject()
            stream.set_data(content.encode("ascii"))
            page.replace_contents(stream)
        writer.add_page(page)
    destination.write_bytes(_writer_bytes(writer))


def _writer_bytes(writer: PdfWriter) -> bytes:
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _font_resources() -> DictionaryObject:
    return DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {
                    NameObject("/F1"): DictionaryObject(
                        {
                            NameObject("/Type"): NameObject("/Font"),
                            NameObject("/Subtype"): NameObject("/Type1"),
                            NameObject("/BaseFont"): NameObject("/Helvetica"),
                        }
                    )
                }
            )
        }
    )


def _format_box(box_in: tuple[float, float, float, float]) -> str:
    return ",".join(str(value) for value in box_in)


def _nonwhite_x_positions(pdf_path: Path, box_in: tuple[float, float, float, float], dpi: int) -> list[int]:
    import pypdfium2

    with pypdfium2.PdfDocument(str(pdf_path)) as document:
        page = document[0]
        bitmap = page.render(scale=dpi / 72.0)
        try:
            width = int(bitmap.width)
            height = int(bitmap.height)
            stride = int(bitmap.stride)
            channels = int(bitmap.n_channels)
            raw = bytes(bitmap.buffer)
            x0, y0, x1, y1 = _box_to_pixel_bounds(box_in=box_in, width_px=width, height_px=height, dpi=dpi)
            xs: list[int] = []
            for y in range(y0, y1):
                row_offset = y * stride
                for x in range(x0, x1):
                    offset = row_offset + x * channels
                    blue = raw[offset]
                    green = raw[offset + 1]
                    red = raw[offset + 2]
                    if red < 240 or green < 240 or blue < 240:
                        xs.append(x - x0)
            return xs
        finally:
            bitmap.close()


def _box_to_pixel_bounds(
    box_in: tuple[float, float, float, float],
    width_px: int,
    height_px: int,
    dpi: int,
) -> tuple[int, int, int, int]:
    x_in, y_in, width_in, height_in = box_in
    left_px = int(round(x_in * dpi))
    bottom_px = int(round(y_in * dpi))
    right_px = int(round((x_in + width_in) * dpi))
    top_px = int(round((y_in + height_in) * dpi))
    return (
        max(0, min(width_px, left_px)),
        max(0, min(height_px, height_px - top_px)),
        max(0, min(width_px, right_px)),
        max(0, min(height_px, height_px - bottom_px)),
    )
