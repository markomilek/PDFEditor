"""Optional rendering-based empty-page detection using PDFium."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any

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
                pixel_count, ink_ratio = _measure_ink_ratio(
                    bitmap=bitmap,
                    sample=sample,
                    background=effective_background,
                )
                is_empty = ink_ratio < ink_threshold
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
                        },
                    )
                )
            except Exception as exc:
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


def _measure_ink_ratio(bitmap: Any, sample: str, background: str) -> tuple[int, float]:
    if background != "white":
        raise ValueError("Only white background sampling is implemented.")

    width = int(bitmap.width)
    height = int(bitmap.height)
    stride = int(bitmap.stride)
    channels = int(bitmap.n_channels)
    if channels < 3:
        raise ValueError("Bitmap must expose at least three color channels.")

    raw = bytes(bitmap.buffer)
    start_x, end_x, start_y, end_y = _sample_bounds(width, height, sample)
    pixel_count = max(0, end_x - start_x) * max(0, end_y - start_y)
    if pixel_count == 0:
        return 0, 0.0

    non_background_pixels = 0
    for y in range(start_y, end_y):
        row_offset = y * stride
        for x in range(start_x, end_x):
            offset = row_offset + x * channels
            if not _pixel_is_white(raw, offset, channels):
                non_background_pixels += 1

    return pixel_count, non_background_pixels / pixel_count


def _sample_bounds(width: int, height: int, sample: str) -> tuple[int, int, int, int]:
    if sample == "all":
        return 0, width, 0, height
    if sample == "center":
        margin_x = int(width * 0.05)
        margin_y = int(height * 0.05)
        return margin_x, max(margin_x, width - margin_x), margin_y, max(margin_y, height - margin_y)
    raise ValueError(f"Unsupported render sample mode: {sample}")


def _pixel_is_white(raw: bytes, offset: int, channels: int) -> bool:
    blue = raw[offset]
    green = raw[offset + 1]
    red = raw[offset + 2]
    if channels >= 4:
        alpha = raw[offset + 3]
        return red == 255 and green == 255 and blue == 255 and alpha in {0, 255}
    return red == 255 and green == 255 and blue == 255
