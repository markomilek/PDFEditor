"""Structural empty-page detection for PDFEditor."""

from __future__ import annotations

from collections.abc import Sequence
import copy
import hashlib
from io import BytesIO
from typing import Any, Callable

from pypdf import PdfReader
from pypdf.generic import ArrayObject

from pdfeditor.models import JSONValue, PageDecision

PAINT_OPERATORS = {
    '"',
    "'",
    "B",
    "B*",
    "BI",
    "Do",
    "F",
    "S",
    "TJ",
    "Tj",
    "b",
    "b*",
    "f",
    "f*",
    "s",
    "sh",
}

STATE_OPERATORS = {
    "BT",
    "CS",
    "ET",
    "G",
    "J",
    "K",
    "M",
    "Q",
    "RG",
    "SC",
    "SCN",
    "TD",
    "TL",
    "Tf",
    "Tm",
    "Tr",
    "Ts",
    "Tw",
    "Tz",
    "W",
    "W*",
    "c",
    "cm",
    "cs",
    "d",
    "g",
    "gs",
    "h",
    "i",
    "j",
    "k",
    "l",
    "m",
    "n",
    "q",
    "re",
    "rg",
    "ri",
    "sc",
    "scn",
    "v",
    "w",
    "y",
}

TEXT_SHOW_OPERATORS = {'"', "'", "TJ", "Tj"}
PATH_PAINT_OPERATORS = {"B", "B*", "F", "S", "b", "b*", "f", "f*", "s", "sh"}


def detect_page_decisions(
    reader: PdfReader,
    treat_annotations_as_empty: bool,
    debug_sink: Callable[[dict[str, JSONValue]], None] | None = None,
) -> list[PageDecision]:
    """Return structured empty-page decisions for each page in a reader."""
    decisions: list[PageDecision] = []
    for page_index, page in enumerate(reader.pages):
        is_empty, reason, details = is_page_empty_structural(
            page,
            treat_annotations_as_empty=treat_annotations_as_empty,
            page_index=page_index,
            debug_sink=debug_sink,
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
    page_index: int | None = None,
    debug_sink: Callable[[dict[str, JSONValue]], None] | None = None,
) -> tuple[bool, str, dict[str, JSONValue]]:
    """Determine whether a page is structurally empty."""
    details: dict[str, JSONValue] = {}
    debug_record = _initialize_debug_record(page=page, page_index=page_index)
    try:
        resources = _resolve_dict(page.get("/Resources"))
        xobject_present = _dict_has_entries(resources.get("/XObject"))
        fonts_present = _dict_has_entries(resources.get("/Font"))
        extgstates_count = _dict_count(resources.get("/ExtGState"))
        annotations_count = _count_entries(page.get("/Annots"))
        raw_contents = page.get("/Contents")
        has_contents = raw_contents is not None
        debug_record.update(
            {
                "annotations_count": annotations_count,
                "contents_object_type": _contents_object_type(raw_contents),
                "extgstates_count": extgstates_count,
                "fonts_count": _dict_count(resources.get("/Font")),
                "has_contents": has_contents,
                "resources_keys_present": _resource_keys(resources),
                "xobjects_count": _dict_count(resources.get("/XObject")),
            }
        )
        details.update(
            {
                "annotations_count": annotations_count,
                "contents_length_bytes": 0,
                "extgstate_hits": [],
                "fonts_present": fonts_present,
                "has_contents": has_contents,
                "invisible_path_events_count": 0,
                "invisible_text_events_count": 0,
                "last_seen_CA": 1.0,
                "last_seen_Tr": 0,
                "last_seen_ca": 1.0,
                "last_seen_font_size": None,
                "notes": [],
                "paint_ops_found": [],
                "paint_ops_seen_count": 0,
                "state_ops_found": [],
                "visible_mark_found": False,
                "xobject_present": xobject_present,
            }
        )
        _merge_content_stream_debug(page=page, debug_record=debug_record)

        if xobject_present:
            return False, "has_xobject", details

        if annotations_count > 0 and not treat_annotations_as_empty:
            return False, "has_annotations", details

        if not has_contents:
            return True, "no_contents", details

        contents = page.get_contents()
        if contents is None:
            return True, "no_contents", details

        try:
            content_data = contents.get_data()
        except Exception as exc:
            _append_debug_exception(debug_record, exc)
            raise
        details["contents_length_bytes"] = len(content_data)
        debug_record["total_contents_bytes"] = len(content_data)

        normalized_data = _strip_pdf_comments_and_whitespace(content_data)
        if not normalized_data:
            return True, "contents_whitespace_only", details

        try:
            operations = list(getattr(contents, "operations", []))
        except Exception as exc:
            _append_debug_exception(debug_record, exc)
            raise
        debug_record["operator_summary"] = _build_operator_summary(operations)
        if not operations and normalized_data:
            return True, "no_paint_ops", details

        result = _evaluate_operations(
            page=page,
            operations=operations,
            details=details,
            debug_record=debug_record,
        )
        if result is not None:
            return result

        if details["paint_ops_seen_count"] > 0:
            return True, "only_invisible_paint", details
        return True, "no_paint_ops", details
    except Exception as exc:
        details["error"] = str(exc)
        return False, "unknown_structure", details
    finally:
        if debug_sink is not None:
            debug_sink(_finalize_debug_record(debug_record))


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


def _dict_count(value: Any) -> int:
    resolved = _resolve_object(value)
    if resolved is None:
        return 0
    if not hasattr(resolved, "items"):
        raise TypeError("Expected a PDF dictionary object.")
    return len(list(resolved.items()))


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


def _evaluate_operations(
    page: Any,
    operations: list[tuple[Any, Any]],
    details: dict[str, JSONValue],
    debug_record: dict[str, JSONValue] | None = None,
) -> tuple[bool, str, dict[str, JSONValue]] | None:
    resources = _resolve_dict(page.get("/Resources"))
    extgstate_resources = _resolve_dict(resources.get("/ExtGState"))
    state = _default_visibility_state()
    stack: list[dict[str, JSONValue]] = []

    for operands, operator in operations:
        operator_name = _operator_name(operator)
        if operator_name == "INLINE IMAGE":
            _record_paint_op(details, "BI")
            details["visible_mark_found"] = True
            return False, "inline_image", details

        if operator_name in STATE_OPERATORS:
            _record_state_op(details, operator_name)

        if operator_name == "q":
            stack.append(copy.deepcopy(state))
            continue
        if operator_name == "Q":
            if stack:
                state = stack.pop()
            else:
                _append_limited(details["notes"], "graphics_state_underflow")
            _sync_last_seen(details, state)
            continue
        if operator_name == "Tr":
            state["text_rendering_mode"] = _to_int(_operand_at(operands, 0), default=state["text_rendering_mode"])
            _record_operator_event(debug_record, "tr_events", {"operator": "Tr", "value": int(state["text_rendering_mode"])})
            _sync_last_seen(details, state)
            continue
        if operator_name == "Tf":
            state["font_size"] = _to_float(_operand_at(operands, 1))
            _record_operator_event(
                debug_record,
                "tf_events",
                {
                    "operator": "Tf",
                    "font": _name_value(_operand_at(operands, 0)),
                    "size": float(state["font_size"]) if state["font_size"] is not None else None,
                },
            )
            _sync_last_seen(details, state)
            continue
        if operator_name == "gs":
            extgstate_name = _name_value(_operand_at(operands, 0))
            if extgstate_name is not None:
                _append_limited(details["extgstate_hits"], extgstate_name)
                state["extgstate_name"] = extgstate_name
                _apply_extgstate(state, extgstate_resources.get(extgstate_name), details)
                _record_operator_event(
                    debug_record,
                    "gs_events",
                    {
                        "operator": "gs",
                        "name": extgstate_name,
                        "ca": float(state["fill_opacity"]),
                        "CA": float(state["stroke_opacity"]),
                    },
                )
            else:
                _append_limited(details["notes"], "gs_without_name")
            _sync_last_seen(details, state)
            continue
        if operator_name in TEXT_SHOW_OPERATORS:
            _record_paint_op(details, operator_name)
            if _text_is_visible(state):
                details["visible_mark_found"] = True
                _sync_last_seen(details, state)
                return False, "visible_text", details
            details["invisible_text_events_count"] = int(details["invisible_text_events_count"]) + 1
            _sync_last_seen(details, state)
            continue
        if operator_name == "Do":
            _record_paint_op(details, operator_name)
            details["visible_mark_found"] = True
            _sync_last_seen(details, state)
            return False, "xobject_paint", details
        if operator_name in PATH_PAINT_OPERATORS:
            _record_paint_op(details, operator_name)
            if _opacity_visible(state):
                details["visible_mark_found"] = True
                _sync_last_seen(details, state)
                return False, "visible_path_paint", details
            details["invisible_path_events_count"] = int(details["invisible_path_events_count"]) + 1
            _sync_last_seen(details, state)
            continue

        _sync_last_seen(details, state)

    return None


def _default_visibility_state() -> dict[str, JSONValue]:
    return {
        "fill_opacity": 1.0,
        "font_size": None,
        "stroke_opacity": 1.0,
        "text_rendering_mode": 0,
        "extgstate_name": None,
    }


def _operator_name(operator: Any) -> str:
    if isinstance(operator, bytes):
        return operator.decode("latin-1")
    return str(operator)


def _operand_at(operands: Any, index: int) -> Any:
    if not isinstance(operands, list):
        return None
    if index >= len(operands):
        return None
    return operands[index]


def _apply_extgstate(
    state: dict[str, JSONValue],
    extgstate_value: Any,
    details: dict[str, JSONValue],
) -> None:
    resolved = _resolve_object(extgstate_value)
    if resolved is None:
        _append_limited(details["notes"], "unknown_extgstate")
        return
    if not hasattr(resolved, "get"):
        _append_limited(details["notes"], "invalid_extgstate")
        return

    fill_opacity = _to_float(resolved.get("/ca"))
    stroke_opacity = _to_float(resolved.get("/CA"))
    if fill_opacity is not None:
        state["fill_opacity"] = fill_opacity
    if stroke_opacity is not None:
        state["stroke_opacity"] = stroke_opacity


def _text_is_visible(state: dict[str, JSONValue]) -> bool:
    if state["text_rendering_mode"] == 3:
        return False
    font_size = state["font_size"]
    if isinstance(font_size, float | int) and float(font_size) == 0:
        return False
    return _opacity_visible(state)


def _opacity_visible(state: dict[str, JSONValue]) -> bool:
    fill_opacity = float(state["fill_opacity"])
    stroke_opacity = float(state["stroke_opacity"])
    return fill_opacity > 0 or stroke_opacity > 0


def _record_paint_op(details: dict[str, JSONValue], operator_name: str) -> None:
    details["paint_ops_seen_count"] = int(details["paint_ops_seen_count"]) + 1
    _append_limited(details["paint_ops_found"], operator_name)


def _record_state_op(details: dict[str, JSONValue], operator_name: str) -> None:
    _append_limited(details["state_ops_found"], operator_name)


def _append_limited(target: JSONValue, value: str, limit: int = 10) -> None:
    if not isinstance(target, list):
        return
    if len(target) >= limit:
        return
    target.append(value)


def _sync_last_seen(details: dict[str, JSONValue], state: dict[str, JSONValue]) -> None:
    details["last_seen_Tr"] = int(state["text_rendering_mode"])
    details["last_seen_font_size"] = (
        float(state["font_size"]) if state["font_size"] is not None else None
    )
    details["last_seen_ca"] = float(state["fill_opacity"])
    details["last_seen_CA"] = float(state["stroke_opacity"])


def _name_value(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _to_float(value: Any, default: float | None = None) -> float | None:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _initialize_debug_record(page: Any, page_index: int | None) -> dict[str, JSONValue]:
    return {
        "annotations_count": 0,
        "contents_object_type": "none",
        "content_streams": [],
        "crop_box": _box_to_dict(getattr(page, "cropbox", None)),
        "extgstates_count": 0,
        "fonts_count": 0,
        "has_contents": False,
        "media_box": _box_to_dict(getattr(page, "mediabox", None)),
        "number_of_content_streams": 0,
        "operator_summary": {
            "gs_events": [],
            "paint_ops_seen": [],
            "parsing_exceptions": [],
            "text_show_ops_seen": [],
            "tf_events": [],
            "top_operators_by_frequency": [],
            "total_operations_count": 0,
            "tr_events": [],
            "unique_operators_count": 0,
            "xobject_paint_seen": False,
        },
        "page_index_0": page_index,
        "page_index_1": page_index + 1 if page_index is not None else None,
        "resources_keys_present": [],
        "total_contents_bytes": 0,
        "xobjects_count": 0,
    }


def _finalize_debug_record(debug_record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    return debug_record


def _box_to_dict(box: Any) -> dict[str, JSONValue] | None:
    if box is None:
        return None
    try:
        return {
            "left": float(box.left),
            "bottom": float(box.bottom),
            "right": float(box.right),
            "top": float(box.top),
        }
    except Exception:
        return {"repr": str(box)}


def _contents_object_type(contents: Any) -> str:
    resolved = _resolve_object(contents)
    if resolved is None:
        return "none"
    if isinstance(resolved, ArrayObject):
        return "array"
    return "single"


def _resource_keys(resources: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    for key in resources:
        keys.append(str(key).lstrip("/"))
    return sorted(keys)


def _merge_content_stream_debug(page: Any, debug_record: dict[str, JSONValue]) -> None:
    raw_contents = page.get("/Contents")
    stream_objects = _content_stream_objects(raw_contents)
    debug_record["number_of_content_streams"] = len(stream_objects)
    previews: list[dict[str, JSONValue]] = []
    total_bytes = 0
    exceptions = _operator_summary(debug_record)["parsing_exceptions"]

    for stream_index, stream_object in enumerate(stream_objects):
        try:
            decoded = bytes(stream_object.get_data())
            total_bytes += len(decoded)
            if stream_index < 3:
                previews.append(
                    {
                        "stream_index": stream_index,
                        "decoded_length_bytes": len(decoded),
                        "first_200_bytes": _safe_preview(decoded[:200]),
                        "last_200_bytes": _safe_preview(decoded[-200:]),
                        "sha256": hashlib.sha256(decoded).hexdigest(),
                    }
                )
        except Exception as exc:
            total_bytes += 0
            _append_limited(exceptions, _exception_text(exc), limit=10)
            if stream_index < 3:
                previews.append(
                    {
                        "stream_index": stream_index,
                        "decoded_length_bytes": None,
                        "error": _exception_text(exc),
                    }
                )

    debug_record["content_streams"] = previews
    debug_record["total_contents_bytes"] = total_bytes


def _content_stream_objects(contents: Any) -> list[Any]:
    resolved = _resolve_object(contents)
    if resolved is None:
        return []
    if isinstance(resolved, ArrayObject):
        return [_resolve_object(item) for item in resolved]
    return [resolved]


def _safe_preview(content: bytes) -> str:
    return repr(content.decode("latin-1", errors="replace"))[1:-1]


def _build_operator_summary(operations: list[tuple[Any, Any]]) -> dict[str, JSONValue]:
    counts: dict[str, int] = {}
    paint_ops_seen: list[str] = []
    text_show_ops_seen: list[str] = []
    xobject_paint_seen = False

    for _, operator in operations:
        operator_name = _operator_name(operator)
        counts[operator_name] = counts.get(operator_name, 0) + 1
        if operator_name in PAINT_OPERATORS:
            _append_limited(paint_ops_seen, operator_name, limit=15)
        if operator_name in TEXT_SHOW_OPERATORS:
            _append_limited(text_show_ops_seen, operator_name, limit=15)
        if operator_name == "Do":
            xobject_paint_seen = True

    top_operators = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:15]
    return {
        "gs_events": [],
        "paint_ops_seen": paint_ops_seen,
        "parsing_exceptions": [],
        "text_show_ops_seen": text_show_ops_seen,
        "tf_events": [],
        "top_operators_by_frequency": [
            {"operator": operator, "count": count} for operator, count in top_operators
        ],
        "total_operations_count": len(operations),
        "tr_events": [],
        "unique_operators_count": len(counts),
        "xobject_paint_seen": xobject_paint_seen,
    }


def _operator_summary(debug_record: dict[str, JSONValue] | None) -> dict[str, JSONValue]:
    if debug_record is None:
        return {}
    summary = debug_record.get("operator_summary")
    if isinstance(summary, dict):
        return summary
    return {}


def _record_operator_event(
    debug_record: dict[str, JSONValue] | None,
    key: str,
    event: dict[str, JSONValue],
) -> None:
    summary = _operator_summary(debug_record)
    target = summary.get(key)
    if not isinstance(target, list) or len(target) >= 10:
        return
    target.append(event)


def _append_debug_exception(debug_record: dict[str, JSONValue], exc: Exception) -> None:
    summary = _operator_summary(debug_record)
    target = summary.get("parsing_exceptions")
    if not isinstance(target, list):
        return
    _append_limited(target, _exception_text(exc), limit=10)


def _exception_text(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"
