"""Single-file processing orchestration for PDFEditor."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from time import perf_counter

from pypdf import PdfReader

from pdfeditor.detect_empty import detect_page_decisions
from pdfeditor.detect_render import detect_empty_pages_render
from pdfeditor.models import FileResult, JSONValue, PageDecision, RunConfig
from pdfeditor.rewrite import rewrite_pdf


def process_pdf(input_path: Path, out_dir: Path, config: RunConfig) -> FileResult:
    """Process one PDF and return a structured file result."""
    warnings: list[str] = []
    errors: list[str] = []
    timings: dict[str, float] = {}
    run_start = perf_counter()
    structural_debug_records: list[dict[str, JSONValue]] = []
    structural_debug_path: Path | None = None

    try:
        reader = PdfReader(str(input_path))
        if reader.is_encrypted:
            raise ValueError("encrypted")
    except Exception as exc:
        status_error = str(exc)
        if status_error == "encrypted":
            errors.append("encrypted")
        else:
            errors.append(f"read_error: {exc}")
        timings["total_seconds"] = round(perf_counter() - run_start, 6)
        return FileResult(
            input_path=str(input_path),
            output_path=None,
            status="failed",
            pages_original=0,
            pages_removed=0,
            pages_output=0,
            decisions_summary={"empty_pages": 0, "non_empty_pages": 0},
            page_decisions=[],
            structural_debug_path=None,
            warnings=warnings,
            errors=errors,
            timings=timings,
        )

    pages_original = len(reader.pages)

    detect_start = perf_counter()
    structural_decisions = detect_page_decisions(
        reader=reader,
        treat_annotations_as_empty=config.treat_annotations_as_empty,
        debug_sink=structural_debug_records.append if config.debug_structural else None,
    )
    render_decisions: list[PageDecision] | None = None
    if config.effective_mode in {"render", "both"}:
        render_decisions = detect_empty_pages_render(
            input_path=input_path,
            dpi=config.render_dpi,
            ink_threshold=config.ink_threshold,
            sample=config.render_sample,
            background=config.effective_background,
        )
    decisions = _combine_decisions(
        structural_decisions=structural_decisions,
        render_decisions=render_decisions,
        mode=config.effective_mode,
    )
    timings["detection_seconds"] = round(perf_counter() - detect_start, 6)

    if config.debug_structural:
        structural_debug_path = _write_structural_debug_artifact(
            input_path=input_path,
            report_dir=Path(config.report_dir),
            records=structural_debug_records,
        )

    pages_to_keep = [
        decision.page_index
        for decision in decisions
        if not decision.is_empty
    ]
    pages_removed = pages_original - len(pages_to_keep)
    pages_output = len(pages_to_keep) if pages_removed else pages_original

    output_path: Path | None = None
    if pages_removed > 0 or config.write_when_unchanged:
        output_path, path_warnings = build_output_path(input_path=input_path, out_dir=out_dir)
        warnings.extend(path_warnings)

    try:
        if config.dry_run:
            status = "dry_run" if pages_removed > 0 else "unchanged"
        elif pages_removed == 0 and not config.write_when_unchanged:
            status = "unchanged"
        elif output_path is None:
            status = "unchanged"
        else:
            write_start = perf_counter()
            rewrite_result = rewrite_pdf(
                input_path=input_path,
                output_path=output_path,
                pages_to_keep=pages_to_keep if pages_removed else list(range(pages_original)),
                bookmark_policy="drop",
            )
            timings["write_seconds"] = round(perf_counter() - write_start, 6)
            warnings.extend(rewrite_result.warnings)
            pages_output = rewrite_result.pages_output
            status = "edited" if pages_removed > 0 else "copied"
    except Exception as exc:
        errors.append(f"rewrite_error: {exc}")
        status = "failed"
        output_path = None
        pages_output = 0

    timings["total_seconds"] = round(perf_counter() - run_start, 6)
    return FileResult(
        input_path=str(input_path),
        output_path=str(output_path) if output_path is not None else None,
        status=status,
        pages_original=pages_original,
        pages_removed=pages_removed,
        pages_output=pages_output,
        decisions_summary=_summarize_decisions(decisions),
        page_decisions=decisions,
        structural_debug_path=str(structural_debug_path) if structural_debug_path is not None else None,
        warnings=warnings,
        errors=errors,
        timings=timings,
    )


def build_output_path(input_path: Path, out_dir: Path) -> tuple[Path, list[str]]:
    """Return a collision-safe edited output path for an input PDF."""
    warnings: list[str] = []
    out_dir.mkdir(parents=True, exist_ok=True)

    candidate = out_dir / f"{input_path.stem}.edited.pdf"
    if not candidate.exists():
        return candidate, warnings

    suffix = 1
    while True:
        candidate = out_dir / f"{input_path.stem}.edited.{suffix}.pdf"
        if not candidate.exists():
            warnings.append(
                f"Output path already existed; wrote to '{candidate.name}' instead."
            )
            return candidate, warnings
        suffix += 1


def _summarize_decisions(decisions: list[PageDecision]) -> dict[str, int]:
    summary: dict[str, int] = {
        "empty_pages": 0,
        "non_empty_pages": 0,
        "no_paint_ops_pages": 0,
        "only_invisible_paint_pages": 0,
        "render_empty_pages": 0,
        "structural_empty_pages": 0,
        "visible_pages": 0,
        "both_empty_pages": 0,
    }
    for decision in decisions:
        summary["empty_pages" if decision.is_empty else "non_empty_pages"] += 1
        summary[decision.reason] = summary.get(decision.reason, 0) + 1
        details = decision.details
        structural_empty = bool(details.get("structural_is_empty"))
        render_empty = bool(details.get("render_is_empty"))
        if structural_empty:
            summary["structural_empty_pages"] += 1
        if render_empty:
            summary["render_empty_pages"] += 1
        if structural_empty and render_empty:
            summary["both_empty_pages"] += 1
        if decision.reason == "only_invisible_paint":
            summary["only_invisible_paint_pages"] += 1
        elif decision.reason in {"no_paint_ops", "no_contents", "contents_whitespace_only"}:
            summary["no_paint_ops_pages"] += 1
        elif not decision.is_empty:
            summary["visible_pages"] += 1
    return summary


def _combine_decisions(
    structural_decisions: list[PageDecision],
    render_decisions: list[PageDecision] | None,
    mode: str,
) -> list[PageDecision]:
    if mode == "structural":
        return [
            _combined_page_decision(
                page_index=decision.page_index,
                structural_decision=decision,
                render_decision=None,
                mode=mode,
            )
            for decision in structural_decisions
        ]
    if render_decisions is None:
        raise ValueError("Render decisions are required for render-based modes.")
    if len(structural_decisions) != len(render_decisions):
        raise ValueError("Structural and render decisions must cover the same number of pages.")
    return [
        _combined_page_decision(
            page_index=structural_decision.page_index,
            structural_decision=structural_decision,
            render_decision=render_decision,
            mode=mode,
        )
        for structural_decision, render_decision in zip(structural_decisions, render_decisions, strict=True)
    ]


def _combined_page_decision(
    page_index: int,
    structural_decision: PageDecision,
    render_decision: PageDecision | None,
    mode: str,
) -> PageDecision:
    structural_is_empty = structural_decision.is_empty
    render_is_empty = render_decision.is_empty if render_decision is not None else False

    if mode == "structural":
        is_empty = structural_is_empty
        reason = "structural_empty" if structural_is_empty else "non_empty"
    elif mode == "render":
        is_empty = render_is_empty
        reason = "render_empty" if render_is_empty else "non_empty"
    elif structural_is_empty and render_is_empty:
        is_empty = True
        reason = "both_empty"
    elif structural_is_empty:
        is_empty = True
        reason = "structural_empty"
    elif render_is_empty:
        is_empty = True
        reason = "render_empty"
    else:
        is_empty = False
        reason = "non_empty"

    details = {
        "structural": structural_decision.details,
        "structural_is_empty": structural_is_empty,
        "structural_reason": structural_decision.reason,
        "render": render_decision.details if render_decision is not None else None,
        "render_is_empty": render_is_empty if render_decision is not None else None,
        "render_reason": render_decision.reason if render_decision is not None else None,
    }
    return PageDecision(
        page_index=page_index,
        is_empty=is_empty,
        reason=reason,
        details=details,
    )


def _write_structural_debug_artifact(
    input_path: Path,
    report_dir: Path,
    records: list[dict[str, JSONValue]],
) -> Path:
    """Write per-page structural debugging information for one processed PDF."""
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate = report_dir / f"structural_debug_{input_path.stem}_{timestamp}.json"
    suffix = 1
    while candidate.exists():
        candidate = report_dir / f"structural_debug_{input_path.stem}_{timestamp}_{suffix}.json"
        suffix += 1

    payload = {
        "input_path": str(input_path),
        "pages": records,
    }
    candidate.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return candidate
