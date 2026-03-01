"""Page-number stamping helpers for corrected output PDFs."""

from __future__ import annotations

from collections.abc import Callable
from io import BytesIO
from typing import Any

from pypdf import PageObject, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from pdfeditor.models import JSONValue

PointBox = tuple[float, float, float, float]
InchBox = tuple[float, float, float, float]


def stamp_page_numbers(
    writer: PdfWriter,
    pages_kept_original_indices: list[int],
    pagenum_box_in: InchBox,
    pagenum_font: str,
    pagenum_size: float,
    pagenum_format: str,
    render_dpi: int,
    white_threshold: int,
    ink_threshold: float,
    force: bool,
    report_hook: Callable[[dict[str, JSONValue]], None] | None,
) -> None:
    """Cover the configured page-number box and stamp corrected output page labels."""
    try:
        pdfium = __import__("pypdfium2")
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Page-number stamping requires optional dependency 'pypdfium2'."
        ) from exc

    if len(writer.pages) != len(pages_kept_original_indices):
        raise ValueError("Writer pages and kept-page mapping must have the same length.")

    for output_page_index, _original_page_index in enumerate(pages_kept_original_indices):
        page = writer.pages[output_page_index]
        page_bytes = _single_page_pdf_bytes(page)
        with pdfium.PdfDocument(page_bytes) as document:
            rendered_page = document[0]
            bitmap = rendered_page.render(scale=render_dpi / 72.0)
            try:
                region_stats = _sample_box_region(
                    bitmap=bitmap,
                    box_in=pagenum_box_in,
                    dpi=render_dpi,
                    white_threshold=white_threshold,
                )
            finally:
                bitmap.close()

        output_page_number = output_page_index + 1
        label = format_page_label(output_page_number, pagenum_format)
        box_pt = _box_in_to_points(pagenum_box_in)

        invalid_sample_area = bool(region_stats["invalid_sample_area"])
        ink_ratio = float(region_stats["ink_ratio"])
        if not force and (invalid_sample_area or ink_ratio > ink_threshold):
            if report_hook is not None:
                report_hook(
                    {
                        "forced": False,
                        "action": "skipped_guardrail",
                        "box_in": list(pagenum_box_in),
                        "box_ink_ratio": ink_ratio,
                        "box_pt": list(box_pt),
                        "cover_color_rgb": list(region_stats["cover_color_rgb"]),
                        "output_page_index": output_page_index,
                        "output_page_number": output_page_number,
                        "reason": (
                            "invalid_sample_area"
                            if invalid_sample_area
                            else "ink_threshold_exceeded"
                        ),
                        "sample_box_px": list(region_stats["sample_box_px"]),
                        "stamped_label": label,
                    }
                )
            continue

        overlay = _create_overlay_page(
            target_page=page,
            box_pt=box_pt,
            label=label,
            font_name=pagenum_font,
            font_size=pagenum_size,
            cover_color_rgb=tuple(int(value) for value in region_stats["cover_color_rgb"]),
        )
        page.merge_page(overlay)

        if report_hook is not None:
            report_hook(
                {
                    "forced": force,
                    "action": "stamped_forced" if force else "stamped",
                    "box_in": list(pagenum_box_in),
                    "box_ink_ratio": ink_ratio,
                    "box_pt": list(box_pt),
                    "cover_color_rgb": list(region_stats["cover_color_rgb"]),
                    "output_page_index": output_page_index,
                    "output_page_number": output_page_number,
                    "reason": "stamped_forced" if force else "stamped",
                    "sample_box_px": list(region_stats["sample_box_px"]),
                    "stamped_label": label,
                }
            )


def format_page_label(output_page_number: int, pagenum_format: str) -> str:
    """Return the formatted page label for one output page."""
    label = pagenum_format
    if "{ROMAN}" in label:
        label = label.replace("{ROMAN}", to_roman(output_page_number))
    if "{roman}" in label:
        label = label.replace("{roman}", to_roman(output_page_number).lower())
    if "{page}" in label:
        label = label.replace("{page}", str(output_page_number))
    return label


def to_roman(value: int) -> str:
    """Convert a positive integer to an uppercase Roman numeral."""
    if value <= 0:
        raise ValueError("Roman numerals require a positive integer.")
    numerals = (
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    )
    remaining = value
    output: list[str] = []
    for number, symbol in numerals:
        while remaining >= number:
            output.append(symbol)
            remaining -= number
    return "".join(output)


def _single_page_pdf_bytes(page: PageObject) -> bytes:
    writer = PdfWriter()
    writer.add_page(page)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _sample_box_region(
    bitmap: Any,
    box_in: InchBox,
    dpi: int,
    white_threshold: int,
) -> dict[str, JSONValue]:
    width = int(bitmap.width)
    height = int(bitmap.height)
    stride = int(bitmap.stride)
    channels = int(bitmap.n_channels)
    raw = bytes(bitmap.buffer)
    x0, y0, x1, y1 = _box_in_to_pixel_bounds(
        box_in=box_in,
        width_px=width,
        height_px=height,
        dpi=dpi,
    )
    pixel_count = max(0, x1 - x0) * max(0, y1 - y0)
    if pixel_count == 0:
        return {
            "cover_color_rgb": [255, 255, 255],
            "ink_ratio": 0.0,
            "invalid_sample_area": True,
            "nonwhite_pixel_count": 0,
            "sample_box_px": [x0, y0, x1, y1],
            "sampled_pixel_count": 0,
        }

    reds: list[int] = []
    greens: list[int] = []
    blues: list[int] = []
    nonwhite_pixel_count = 0
    for y in range(y0, y1):
        row_offset = y * stride
        for x in range(x0, x1):
            offset = row_offset + x * channels
            blue = raw[offset]
            green = raw[offset + 1]
            red = raw[offset + 2]
            alpha = raw[offset + 3] if channels >= 4 else None
            reds.append(red)
            greens.append(green)
            blues.append(blue)
            if not _pixel_is_white(red=red, green=green, blue=blue, alpha=alpha, white_threshold=white_threshold):
                nonwhite_pixel_count += 1

    cover_color_rgb = [_median_channel(reds), _median_channel(greens), _median_channel(blues)]
    return {
        "cover_color_rgb": cover_color_rgb,
        "ink_ratio": nonwhite_pixel_count / pixel_count,
        "invalid_sample_area": False,
        "nonwhite_pixel_count": nonwhite_pixel_count,
        "sample_box_px": [x0, y0, x1, y1],
        "sampled_pixel_count": pixel_count,
    }


def _box_in_to_pixel_bounds(
    box_in: InchBox,
    width_px: int,
    height_px: int,
    dpi: int,
) -> tuple[int, int, int, int]:
    x_in, y_in, width_in, height_in = box_in
    left_px = int(round(x_in * dpi))
    bottom_px = int(round(y_in * dpi))
    right_px = int(round((x_in + width_in) * dpi))
    top_px = int(round((y_in + height_in) * dpi))
    x0 = max(0, min(width_px, left_px))
    x1 = max(0, min(width_px, right_px))
    y0 = max(0, min(height_px, height_px - top_px))
    y1 = max(0, min(height_px, height_px - bottom_px))
    return (x0, y0, x1, y1)


def _box_in_to_points(box_in: InchBox) -> PointBox:
    x_in, y_in, width_in, height_in = box_in
    return (x_in * 72.0, y_in * 72.0, width_in * 72.0, height_in * 72.0)


def _create_overlay_page(
    target_page: PageObject,
    box_pt: PointBox,
    label: str,
    font_name: str,
    font_size: float,
    cover_color_rgb: tuple[int, int, int],
) -> PageObject:
    width_pt = float(target_page.mediabox.width)
    height_pt = float(target_page.mediabox.height)
    overlay = PageObject.create_blank_page(width=width_pt, height=height_pt)
    overlay[NameObject("/Resources")] = _overlay_resources(font_name)
    overlay.replace_contents(_overlay_stream(
        box_pt=box_pt,
        label=label,
        font_resource_name="/F1",
        font_family=font_name,
        font_size=font_size,
        cover_color_rgb=cover_color_rgb,
    ))
    return overlay


def _overlay_resources(font_name: str) -> DictionaryObject:
    return DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {
                    NameObject("/F1"): DictionaryObject(
                        {
                            NameObject("/Type"): NameObject("/Font"),
                            NameObject("/Subtype"): NameObject("/Type1"),
                            NameObject("/BaseFont"): NameObject(f"/{font_name}"),
                        }
                    )
                }
            )
        }
    )


def _overlay_stream(
    box_pt: PointBox,
    label: str,
    font_resource_name: str,
    font_family: str,
    font_size: float,
    cover_color_rgb: tuple[int, int, int],
) -> DecodedStreamObject:
    x_pt, y_pt, width_pt, height_pt = box_pt
    cx = x_pt + (width_pt / 2.0)
    cy = y_pt + (height_pt / 2.0)
    text_width_pt = _estimate_text_width(label, font_size, font_family=font_family)
    text_x = cx - (text_width_pt / 2.0)
    text_y = cy - (font_size * 0.35)
    fill_r, fill_g, fill_b = _rgb_to_pdf(cover_color_rgb)
    text_rgb = _text_color_rgb(cover_color_rgb)
    text_r, text_g, text_b = _rgb_to_pdf(text_rgb)
    text_object = _pdf_string(label)
    content = (
        f"q {fill_r:.6f} {fill_g:.6f} {fill_b:.6f} rg {x_pt:.3f} {y_pt:.3f} {width_pt:.3f} {height_pt:.3f} re f Q "
        f"q BT {font_resource_name} {font_size:.3f} Tf {text_r:.6f} {text_g:.6f} {text_b:.6f} rg "
        f"1 0 0 1 {text_x:.3f} {text_y:.3f} Tm {text_object} Tj ET Q"
    ).encode("utf-8")
    stream = DecodedStreamObject()
    stream.set_data(content)
    return stream


def _estimate_text_width(label: str, font_size: float, font_family: str) -> float:
    per_font = {
        "Courier": 0.60,
        "Helvetica": 0.56,
        "Times-Roman": 0.50,
    }
    average = per_font.get(font_family, 0.56)
    return font_size * average * len(label)


def _pdf_string(text: str) -> str:
    if all(ord(char) < 128 for char in text):
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        return f"({escaped})"
    encoded = ("\ufeff" + text).encode("utf-16-be").hex().upper()
    return f"<{encoded}>"


def _rgb_to_pdf(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    red, green, blue = rgb
    return (red / 255.0, green / 255.0, blue / 255.0)


def _text_color_rgb(cover_color_rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    red, green, blue = cover_color_rgb
    luminance = (0.299 * red) + (0.587 * green) + (0.114 * blue)
    return (0, 0, 0) if luminance >= 186 else (255, 255, 255)


def _median_channel(values: list[int]) -> int:
    ordered = sorted(values)
    middle = len(ordered) // 2
    return ordered[middle]


def _pixel_is_white(
    red: int,
    green: int,
    blue: int,
    alpha: int | None,
    white_threshold: int,
) -> bool:
    if alpha == 0:
        return True
    return red >= white_threshold and green >= white_threshold and blue >= white_threshold
