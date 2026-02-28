"""Deterministic PDF fixture builders for scaffold tests."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Literal

from pypdf import PageObject, PdfWriter
from pypdf.generic import (
    ArrayObject,
    BooleanObject,
    DecodedStreamObject,
    DictionaryObject,
    FloatObject,
    NameObject,
    NumberObject,
    TextStringObject,
)

PageKind = Literal[
    "empty",
    "font_resources_only",
    "invisible_text_opacity_zero",
    "invisible_text_tr3",
    "invisible_text_zero_font_size",
    "state_ops_only",
    "text",
    "footer_page_number",
    "annotation_only",
    "whitespace_only",
    "shape",
]

PAGE_WIDTH = 612
PAGE_HEIGHT = 792


@dataclass(frozen=True)
class PageSpec:
    """Describe a deterministic synthetic page for tests."""

    kind: PageKind
    text: str | None = None


@dataclass(frozen=True)
class OutlineSpec:
    """Describe a single outline item for generated PDFs."""

    title: str
    page_index: int


def create_pdf_with_pages(
    page_specs: list[PageSpec],
    outline_specs: list[OutlineSpec] | None = None,
) -> bytes:
    """Build a deterministic PDF payload from synthetic page specifications."""
    writer = PdfWriter()

    for page_index, page_spec in enumerate(page_specs):
        page = PageObject.create_blank_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        _apply_page_spec(page, page_spec)
        writer.add_page(page)
        if page_spec.kind == "annotation_only":
            writer.add_annotation(page_index, _build_text_annotation())

    for outline_spec in outline_specs or []:
        writer.add_outline_item(outline_spec.title, outline_spec.page_index)

    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def write_pdf_with_pages(
    destination: Path,
    page_specs: list[PageSpec],
    outline_specs: list[OutlineSpec] | None = None,
) -> Path:
    """Write a deterministic synthetic PDF to disk and return its path."""
    destination.write_bytes(create_pdf_with_pages(page_specs, outline_specs))
    return destination


def empty_page() -> PageSpec:
    """Return a truly empty page specification."""
    return PageSpec(kind="empty")


def text_page(text: str) -> PageSpec:
    """Return a page specification with a small text fragment."""
    return PageSpec(kind="text", text=text)


def font_resources_only_page() -> PageSpec:
    """Return a visually blank page that still carries font resources."""
    return PageSpec(kind="font_resources_only")


def invisible_text_tr3_page() -> PageSpec:
    """Return a page with invisible text via rendering mode Tr=3."""
    return PageSpec(kind="invisible_text_tr3")


def invisible_text_zero_font_size_page() -> PageSpec:
    """Return a page with invisible text via font size 0."""
    return PageSpec(kind="invisible_text_zero_font_size")


def invisible_text_opacity_zero_page() -> PageSpec:
    """Return a page with invisible text via zero-opacity ExtGState."""
    return PageSpec(kind="invisible_text_opacity_zero")


def state_ops_only_page() -> PageSpec:
    """Return a page with only state/layout operators and no painting ops."""
    return PageSpec(kind="state_ops_only")


def footer_page_number_page(text: str) -> PageSpec:
    """Return a page specification with footer page-number text."""
    return PageSpec(kind="footer_page_number", text=text)


def annotation_only_page() -> PageSpec:
    """Return a page specification containing only an annotation."""
    return PageSpec(kind="annotation_only")


def whitespace_only_page() -> PageSpec:
    """Return a page specification with a whitespace-only content stream."""
    return PageSpec(kind="whitespace_only")


def shape_page() -> PageSpec:
    """Return a page specification with a simple stroked rectangle."""
    return PageSpec(kind="shape")


def create_wordlike_blank_then_text_pdf(text: str = "Visible text") -> bytes:
    """Build a two-page PDF with a blank page carrying copied font resources."""
    writer = PdfWriter()

    blank_page = PageObject.create_blank_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    text_content_page = PageObject.create_blank_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    _apply_text_content(text_content_page, text, x=72, y=700)

    blank_page[NameObject("/Resources")] = DictionaryObject(text_content_page["/Resources"])
    _apply_raw_content(blank_page, b"q 1 0 0 1 0 0 cm BT ET Q")

    writer.add_page(blank_page)
    writer.add_page(text_content_page)

    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _apply_page_spec(page: PageObject, page_spec: PageSpec) -> None:
    if page_spec.kind == "empty":
        return
    if page_spec.kind == "font_resources_only":
        page[NameObject("/Resources")] = _font_resources_dictionary()
        return
    if page_spec.kind == "invisible_text_tr3":
        page[NameObject("/Resources")] = _font_resources_dictionary()
        _apply_raw_content(page, b"BT 3 Tr /F1 12 Tf 72 720 Td (Invisible) Tj ET")
        return
    if page_spec.kind == "invisible_text_zero_font_size":
        page[NameObject("/Resources")] = _font_resources_dictionary()
        _apply_raw_content(page, b"BT /F1 0 Tf 72 720 Td (Invisible) Tj ET")
        return
    if page_spec.kind == "invisible_text_opacity_zero":
        page[NameObject("/Resources")] = _font_resources_dictionary_with_zero_opacity()
        _apply_raw_content(page, b"/GS0 gs BT /F1 12 Tf 72 720 Td (InvisibleByOpacity) Tj ET")
        return
    if page_spec.kind == "state_ops_only":
        _apply_raw_content(page, b"q 1 0 0 1 0 0 cm BT ET Q")
        return
    if page_spec.kind == "text":
        _apply_text_content(page, page_spec.text or "1", x=72, y=700)
        return
    if page_spec.kind == "footer_page_number":
        _apply_text_content(page, page_spec.text or "Page 1", x=72, y=36)
        return
    if page_spec.kind == "annotation_only":
        return
    if page_spec.kind == "whitespace_only":
        _apply_raw_content(page, b" \n\t \n")
        return
    if page_spec.kind == "shape":
        _apply_raw_content(page, b"0 0 0 RG 72 72 144 72 re S")
        return
    raise ValueError(f"Unsupported page kind: {page_spec.kind}")


def _apply_text_content(page: PageObject, text: str, x: int, y: int) -> None:
    page[NameObject("/Resources")] = _font_resources_dictionary()
    escaped_text = _escape_pdf_text(text)
    content = f"BT /F1 12 Tf {x} {y} Td ({escaped_text}) Tj ET".encode("ascii")
    _apply_raw_content(page, content)


def _apply_raw_content(page: PageObject, content: bytes) -> None:
    stream = DecodedStreamObject()
    stream.set_data(content)
    page.replace_contents(stream)


def _build_text_annotation() -> DictionaryObject:
    return DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Annot"),
            NameObject("/Subtype"): NameObject("/Text"),
            NameObject("/Rect"): ArrayObject(
                [
                    FloatObject(36),
                    FloatObject(36),
                    FloatObject(72),
                    FloatObject(72),
                ]
            ),
            NameObject("/Contents"): TextStringObject("annotation-only page"),
            NameObject("/Name"): NameObject("/Comment"),
            NameObject("/Open"): BooleanObject(False),
            NameObject("/F"): NumberObject(4),
        }
    )


def _font_resources_dictionary() -> DictionaryObject:
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


def _font_resources_dictionary_with_zero_opacity() -> DictionaryObject:
    resources = _font_resources_dictionary()
    resources[NameObject("/ExtGState")] = DictionaryObject(
        {
            NameObject("/GS0"): DictionaryObject(
                {
                    NameObject("/Type"): NameObject("/ExtGState"),
                    NameObject("/ca"): FloatObject(0),
                    NameObject("/CA"): FloatObject(0),
                }
            )
        }
    )
    return resources


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
