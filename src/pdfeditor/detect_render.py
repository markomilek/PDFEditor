"""Optional rendering-based empty-page detection using PDFium."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any, Callable

from pdfeditor.models import JSONValue, PageDecision


def is_render_backend_available() -> bool:
    """Return whether pypdfium2 is importable."""
    try:
        import_module("pypdfium2")
    except ModuleNotFoundError:
        return False
    return True


def get_render_backend_version() -> str | None:
    """Return the installed pypdfium2 version string if available."""
    try:
        pdfium = import_module("pypdfium2")
    except ModuleNotFoundError:
        return None
    version_module = getattr(pdfium, "version", None)
    if version_module is None:
        return None
    return getattr(version_module, "PYPDFIUM_INFO", None)


def detect_empty_pages_render(
    input_path: Path,
    dpi: int,
    ink_threshold: float,
    sample: str = "all",
    background: str = "white",
    white_threshold: int = 240,
    center_margin: float = 0.05,
    debug_sink: Callable[[dict[str, JSONValue]], None] | None = None,
) -> list[PageDecision]:
    """Render each page and classify it by ink ratio against a white background."""
    try:
        pdfium = import_module("pypdfium2")
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Rendering mode requires optional dependency 'pypdfium2'."
        ) from exc

    effective_background = "white"
    document = pdfium.PdfDocument(str(input_path))
    decisions: list[PageDecision] = []
    scale = dpi / 72.0

    try:
        for page_index in range(len(document)):
            page = document[page_index]
            bitmap = None
            try:
                bitmap = page.render(scale=scale)
                diagnostics = _measure_ink_ratio(
                    bitmap=bitmap,
                    sample=sample,
                    background=effective_background,
                    white_threshold=white_threshold,
                    center_margin=center_margin,
                )
                pixel_count = int(diagnostics["total_pixels_sampled"])
                ink_ratio = float(diagnostics["ink_ratio"])
                is_empty = ink_ratio < ink_threshold
                if debug_sink is not None:
                    debug_sink(
                        {
                            "page_index_0": page_index,
                            "page_index_1": page_index + 1,
                            "ink_ratio": ink_ratio,
                            "is_empty_by_render": is_empty,
                            "reason": "ink_below_threshold" if is_empty else "ink_above_threshold",
                            **diagnostics,
                        }
                    )
                decisions.append(
                    PageDecision(
                        page_index=page_index,
                        is_empty=is_empty,
                        reason="ink_below_threshold" if is_empty else "ink_above_threshold",
                        details={
                            "dpi": dpi,
                            "ink_ratio": ink_ratio,
                            "pixel_count": pixel_count,
                            "sample": sample,
                            "background": effective_background,
                            "white_threshold": white_threshold,
                        },
                    )
                )
            except Exception as exc:
                if debug_sink is not None:
                    debug_sink(
                        {
                            "page_index_0": page_index,
                            "page_index_1": page_index + 1,
                            "ink_ratio": None,
                            "is_empty_by_render": False,
                            "reason": "render_failed",
                            "dpi": dpi,
                            "sample": sample,
                            "background": effective_background,
                            "white_threshold": white_threshold,
                            "center_margin": center_margin,
                            "error": str(exc),
                        }
                    )
                decisions.append(
                    PageDecision(
                        page_index=page_index,
                        is_empty=False,
                        reason="render_failed",
                        details={
                            "dpi": dpi,
                            "ink_ratio": None,
                            "pixel_count": 0,
                            "sample": sample,
                            "background": effective_background,
                            "white_threshold": white_threshold,
                            "error": str(exc),
                        },
                    )
                )
            finally:
                if bitmap is not None:
                    bitmap.close()
    finally:
        close = getattr(document, "close", None)
        if callable(close):
            close()

    return decisions


def _measure_ink_ratio(
    bitmap: Any,
    sample: str,
    background: str,
    white_threshold: int,
    center_margin: float,
) -> dict[str, JSONValue]:
    if background != "white":
        raise ValueError("Only white background sampling is implemented.")

    width = int(bitmap.width)
    height = int(bitmap.height)
    stride = int(bitmap.stride)
    channels = int(bitmap.n_channels)
    if channels < 3:
        raise ValueError("Bitmap must expose at least three color channels.")

    raw = bytes(bitmap.buffer)
    start_x, end_x, start_y, end_y = _sample_bounds(width, height, sample, center_margin)
    pixel_count = max(0, end_x - start_x) * max(0, end_y - start_y)
    if pixel_count == 0:
        return {
            "center_margin": center_margin,
            "height_px": height,
            "ink_ratio": 0.0,
            "max_alpha": None,
            "max_rgb": [0, 0, 0],
            "min_alpha": None,
            "min_rgb": [255, 255, 255],
            "nonwhite_pixels": 0,
            "pixel_format": _pixel_format(channels),
            "sample": sample,
            "sample_box_px": [start_x, start_y, end_x, end_y],
            "total_pixels_sampled": 0,
            "white_threshold": white_threshold,
            "width_px": width,
        }

    non_background_pixels = 0
    min_rgb = [255, 255, 255]
    max_rgb = [0, 0, 0]
    min_alpha: int | None = 255 if channels >= 4 else None
    max_alpha: int | None = 0 if channels >= 4 else None
    for y in range(start_y, end_y):
        row_offset = y * stride
        for x in range(start_x, end_x):
            offset = row_offset + x * channels
            blue = raw[offset]
            green = raw[offset + 1]
            red = raw[offset + 2]
            min_rgb[0] = min(min_rgb[0], red)
            min_rgb[1] = min(min_rgb[1], green)
            min_rgb[2] = min(min_rgb[2], blue)
            max_rgb[0] = max(max_rgb[0], red)
            max_rgb[1] = max(max_rgb[1], green)
            max_rgb[2] = max(max_rgb[2], blue)
            alpha = raw[offset + 3] if channels >= 4 else None
            if alpha is not None and min_alpha is not None and max_alpha is not None:
                min_alpha = min(min_alpha, alpha)
                max_alpha = max(max_alpha, alpha)
            if not _pixel_is_white(
                red=red,
                green=green,
                blue=blue,
                alpha=alpha,
                white_threshold=white_threshold,
            ):
                non_background_pixels += 1

    return {
        "center_margin": center_margin,
        "height_px": height,
        "ink_ratio": non_background_pixels / pixel_count,
        "max_alpha": max_alpha,
        "max_rgb": max_rgb,
        "min_alpha": min_alpha,
        "min_rgb": min_rgb,
        "nonwhite_pixels": non_background_pixels,
        "pixel_format": _pixel_format(channels),
        "sample": sample,
        "sample_box_px": [start_x, start_y, end_x, end_y],
        "total_pixels_sampled": pixel_count,
        "white_threshold": white_threshold,
        "width_px": width,
    }


def _sample_bounds(
    width: int,
    height: int,
    sample: str,
    center_margin: float,
) -> tuple[int, int, int, int]:
    if sample == "all":
        return 0, width, 0, height
    if sample == "center":
        margin_x = int(width * center_margin)
        margin_y = int(height * center_margin)
        return margin_x, max(margin_x, width - margin_x), margin_y, max(margin_y, height - margin_y)
    raise ValueError(f"Unsupported render sample mode: {sample}")


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


def _pixel_format(channels: int) -> str:
    if channels == 4:
        return "BGRx_or_BGRA"
    if channels == 3:
        return "BGR"
    return f"{channels}_channels"
