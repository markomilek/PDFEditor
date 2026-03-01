"""PDF rewrite helpers for removing empty pages safely."""

from __future__ import annotations

from collections.abc import Collection
from pathlib import Path
import re
from typing import Any

from pypdf import PdfReader, PdfWriter

from pdfeditor.models import JSONValue, RewriteResult
from pdfeditor.stamp_page_numbers import stamp_page_numbers

EDITED_NAME_PATTERN = re.compile(r"\.edited(?:\.\d+)?\.pdf\Z", re.IGNORECASE)


def rewrite_pdf(
    input_path: Path,
    output_path: Path,
    pages_to_keep: list[int],
    bookmark_policy: str = "drop",
    stamp_config: dict[str, JSONValue] | None = None,
) -> RewriteResult:
    """Rewrite a PDF while retaining only the requested page indexes."""
    if bookmark_policy != "drop":
        raise ValueError("Only the 'drop' bookmark policy is supported.")
    _validate_output_path(output_path)

    reader = PdfReader(str(input_path))
    writer = PdfWriter()
    warnings: list[str] = []

    keep_list = list(pages_to_keep)
    full_keep = keep_list == list(range(len(reader.pages)))
    stamp_decisions: list[dict[str, JSONValue]] = []
    if full_keep:
        writer.clone_document_from_reader(reader)
        pages_output = len(reader.pages)
        outlines_copied = 0
        outlines_dropped = 0
    else:
        for page_index in keep_list:
            writer.add_page(reader.pages[page_index])
        _copy_metadata(reader, writer)
        outlines_copied, outlines_dropped, outline_warnings = _copy_outlines(
            reader=reader,
            writer=writer,
            page_index_map={old_index: new_index for new_index, old_index in enumerate(keep_list)},
        )
        warnings.extend(outline_warnings)
        named_destinations = getattr(reader, "named_destinations", {})
        if named_destinations:
            warnings.append(
                f"Dropped {len(named_destinations)} named destination(s) during rewrite."
            )
        pages_output = len(keep_list)

    if stamp_config is not None:
        stamp_page_numbers(
            writer=writer,
            pages_kept_original_indices=keep_list if keep_list else list(range(len(writer.pages))),
            pagenum_box_in=_tuple4(stamp_config["pagenum_box"]),
            pagenum_font=str(stamp_config["pagenum_font"]),
            pagenum_size=float(stamp_config["pagenum_size"]),
            pagenum_format=str(stamp_config["pagenum_format"]),
            render_dpi=int(stamp_config["render_dpi"]),
            white_threshold=int(stamp_config["white_threshold"]),
            ink_threshold=float(stamp_config["ink_threshold"]),
            force=bool(stamp_config["force"]),
            report_hook=stamp_decisions.append,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as handle:
        writer.write(handle)

    return RewriteResult(
        output_path=str(output_path),
        pages_output=pages_output,
        outlines_copied=outlines_copied,
        outlines_dropped=outlines_dropped,
        stamp_decisions=stamp_decisions,
        stamping_applied_pages=sum(
            1 for decision in stamp_decisions if decision.get("action") in {"stamped", "stamped_forced"}
        ),
        stamping_forced_pages=sum(
            1 for decision in stamp_decisions if decision.get("action") == "stamped_forced"
        ),
        stamping_skipped_pages=sum(
            1 for decision in stamp_decisions if decision.get("action") == "skipped_guardrail"
        ),
        warnings=warnings,
    )


def rewrite_pdf_removing_pages(
    input_path: Path,
    output_path: Path,
    pages_to_remove: Collection[int],
) -> Path:
    """Rewrite a PDF while removing the specified zero-based page indexes."""
    reader = PdfReader(str(input_path))
    remove_indexes = set(pages_to_remove)
    pages_to_keep = [
        page_index
        for page_index in range(len(reader.pages))
        if page_index not in remove_indexes
    ]
    rewrite_pdf(
        input_path=input_path,
        output_path=output_path,
        pages_to_keep=pages_to_keep,
        bookmark_policy="drop",
    )
    return output_path


def _validate_output_path(output_path: Path) -> None:
    if not EDITED_NAME_PATTERN.search(output_path.name):
        raise ValueError(
            "Output path must follow the edited PDF naming scheme "
            "('<stem>.edited.pdf' or '<stem>.edited.<n>.pdf')."
        )


def _copy_metadata(reader: PdfReader, writer: PdfWriter) -> None:
    metadata = getattr(reader, "metadata", None)
    if not metadata:
        return
    safe_metadata = {
        str(key): str(value)
        for key, value in metadata.items()
        if isinstance(key, str) and value is not None
    }
    if safe_metadata:
        writer.add_metadata(safe_metadata)


def _copy_outlines(
    reader: PdfReader,
    writer: PdfWriter,
    page_index_map: dict[int, int],
) -> tuple[int, int, list[str]]:
    warnings: list[str] = []
    try:
        outline = reader.outline
    except Exception as exc:
        return 0, 0, [f"Dropped all outlines due to outline read error: {exc}"]

    if not outline:
        return 0, 0, warnings

    try:
        copied, dropped = _copy_outline_entries(
            entries=outline,
            parent=None,
            reader=reader,
            writer=writer,
            page_index_map=page_index_map,
        )
    except Exception as exc:
        return 0, 0, [f"Dropped all outlines due to outline copy error: {exc}"]

    if dropped:
        warnings.append(
            f"Dropped {dropped} outline item(s) that referenced removed or unsupported pages."
        )
    return copied, dropped, warnings


def _copy_outline_entries(
    entries: list[Any],
    parent: Any,
    reader: PdfReader,
    writer: PdfWriter,
    page_index_map: dict[int, int],
) -> tuple[int, int]:
    copied = 0
    dropped = 0
    index = 0

    while index < len(entries):
        entry = entries[index]
        if isinstance(entry, list):
            child_copied, child_dropped = _copy_outline_entries(
                entries=entry,
                parent=parent,
                reader=reader,
                writer=writer,
                page_index_map=page_index_map,
            )
            copied += child_copied
            dropped += child_dropped
            index += 1
            continue

        children: list[Any] | None = None
        if index + 1 < len(entries) and isinstance(entries[index + 1], list):
            children = entries[index + 1]

        destination_page = reader.get_destination_page_number(entry)
        copied_parent = parent
        if destination_page is not None and destination_page in page_index_map:
            copied_parent = writer.add_outline_item(
                title=_get_outline_title(entry),
                page_number=page_index_map[destination_page],
                parent=parent,
                is_open=bool(entry.get("/%is_open%", True)),
            )
            copied += 1
        else:
            dropped += 1

        if children is not None:
            child_copied, child_dropped = _copy_outline_entries(
                entries=children,
                parent=copied_parent if destination_page in page_index_map else parent,
                reader=reader,
                writer=writer,
                page_index_map=page_index_map,
            )
            copied += child_copied
            dropped += child_dropped
            index += 1

        index += 1

    return copied, dropped


def _get_outline_title(entry: Any) -> str:
    title = getattr(entry, "title", None) or entry.get("/Title")
    if not title:
        return "Untitled"
    return str(title)


def _tuple4(value: JSONValue) -> tuple[float, float, float, float]:
    if not isinstance(value, list | tuple) or len(value) != 4:
        raise ValueError("Expected a 4-value box tuple for page-number stamping.")
    first, second, third, fourth = value
    return (float(first), float(second), float(third), float(fourth))
