"""Structural empty-page detection for PDFEditor."""

from __future__ import annotations

from io import BytesIO
from collections.abc import Sequence
from typing import Any

from pypdf import PdfReader

from pdfeditor.models import JSONValue, PageDecision


def detect_page_decisions(
    reader: PdfReader,
    treat_annotations_as_empty: bool,
) -> list[PageDecision]:
    """Return structured empty-page decisions for each page in a reader."""
    decisions: list[PageDecision] = []
    for page_index, page in enumerate(reader.pages):
        is_empty, reason, details = is_page_empty_structural(
            page,
            treat_annotations_as_empty=treat_annotations_as_empty,
        )
        decisions.append(
            PageDecision(
                page_index=page_index,
                is_empty=is_empty,
                reason=reason,
                details=details,
            )
        )
    return decisions


def detect_empty_pages(
    pdf_bytes: bytes,
    treat_annotations_as_empty: bool = True,
) -> Sequence[bool]:
    """Return per-page empty-page decisions for a PDF payload."""
    reader = PdfReader(BytesIO(pdf_bytes))
    if reader.is_encrypted:
        raise ValueError("Encrypted PDFs are not supported.")
    return [
        decision.is_empty
        for decision in detect_page_decisions(
            reader,
            treat_annotations_as_empty=treat_annotations_as_empty,
        )
    ]


def is_page_empty_structural(
    page: Any,
    treat_annotations_as_empty: bool,
) -> tuple[bool, str, dict[str, JSONValue]]:
    """Determine whether a page is structurally empty."""
    details: dict[str, JSONValue] = {
        "treat_annotations_as_empty": treat_annotations_as_empty,
    }
    try:
        resources = _resolve_dict(page.get("/Resources"))
        details["resource_keys"] = sorted(resources.keys())

        has_xobject = _dict_has_entries(resources.get("/XObject"))
        details["has_xobject"] = has_xobject
        if has_xobject:
            return False, "has_xobject", details

        has_fonts = _dict_has_entries(resources.get("/Font"))
        details["has_fonts"] = has_fonts
        if has_fonts:
            return False, "has_fonts", details

        annotation_count = _count_entries(page.get("/Annots"))
        details["annotation_count"] = annotation_count
        if annotation_count > 0 and not treat_annotations_as_empty:
            return False, "has_annotations", details

        has_contents = page.get("/Contents") is not None
        details["has_contents"] = has_contents
        if not has_contents:
            return True, "no_contents", details

        contents = page.get_contents()
        if contents is None:
            return True, "no_contents", details

        operations = list(getattr(contents, "operations", []))
        details["operation_count"] = len(operations)
        if operations:
            return False, "has_content_operations", details

        content_data = contents.get_data()
        normalized_data = _strip_pdf_comments_and_whitespace(content_data)
        details["content_bytes"] = len(content_data)
        details["normalized_content_bytes"] = len(normalized_data)
        if normalized_data:
            return False, "has_content_bytes", details
        return True, "contents_whitespace_only", details
    except Exception as exc:
        details["error"] = str(exc)
        return False, "unknown_structure", details


def _resolve_object(value: Any) -> Any:
    if value is None:
        return None
    get_object = getattr(value, "get_object", None)
    if callable(get_object):
        return get_object()
    return value


def _resolve_dict(value: Any) -> dict[str, Any]:
    resolved = _resolve_object(value)
    if resolved is None:
        return {}
    if not hasattr(resolved, "items"):
        raise TypeError("Expected a PDF dictionary object.")
    return {str(key): item for key, item in resolved.items()}


def _dict_has_entries(value: Any) -> bool:
    resolved = _resolve_object(value)
    if resolved is None:
        return False
    if not hasattr(resolved, "items"):
        raise TypeError("Expected a PDF dictionary object.")
    return len(list(resolved.items())) > 0


def _count_entries(value: Any) -> int:
    resolved = _resolve_object(value)
    if resolved is None:
        return 0
    if hasattr(resolved, "__len__"):
        return len(resolved)
    raise TypeError("Expected a PDF array-like object.")


def _strip_pdf_comments_and_whitespace(content: bytes) -> bytes:
    output = bytearray()
    in_comment = False
    for byte in content:
        if in_comment:
            if byte in (10, 13):
                in_comment = False
            continue
        if byte == 37:
            in_comment = True
            continue
        if chr(byte).isspace():
            continue
        output.append(byte)
    return bytes(output)
