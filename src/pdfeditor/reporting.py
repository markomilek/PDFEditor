"""Run report generation for PDFEditor."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import getpass
from pathlib import Path
import platform
import sys
from typing import Any

import pypdf

from pdfeditor.detect_render import get_render_backend_version
from pdfeditor.models import JSONValue, FileResult, RunConfig, RunResult


def build_run_result(
    config: RunConfig,
    files: list[FileResult],
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
) -> RunResult:
    """Build an aggregated run result with environment metadata."""
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone()
    return RunResult(
        timestamp_local=now_local.isoformat(),
        timestamp_utc=now_utc.isoformat(),
        user=getpass.getuser(),
        host=platform.node(),
        python_version=sys.version.split()[0],
        pypdf_version=pypdf.__version__,
        pypdfium2_version=get_render_backend_version(),
        config=config,
        files=files,
        totals=_build_totals(files),
        warnings=list(warnings or []),
        errors=list(errors or []),
    )


def write_run_reports(run_result: RunResult, report_dir: Path) -> tuple[Path, Path]:
    """Write machine-readable and text run reports."""
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = _timestamp_for_filename(run_result.timestamp_local)
    json_path = report_dir / f"run_report_{timestamp}.json"
    txt_path = report_dir / f"run_report_{timestamp}.txt"

    json_path.write_text(_json_text(run_result), encoding="utf-8")
    txt_path.write_text(_text_report(run_result), encoding="utf-8")
    return json_path, txt_path


def run_result_to_dict(run_result: RunResult) -> dict[str, JSONValue]:
    """Convert a run result to a JSON-serializable dictionary."""
    serialized = _serialize_value(run_result)
    if not isinstance(serialized, dict):
        raise TypeError("RunResult serialization must produce a dictionary.")
    return serialized


def _build_totals(files: list[FileResult]) -> dict[str, int]:
    totals = {
        "files_found": len(files),
        "files_processed": sum(1 for file in files if file.status != "failed"),
        "files_failed": sum(1 for file in files if file.status == "failed"),
        "files_written": sum(1 for file in files if file.status in {"edited", "copied"}),
        "files_edited": sum(1 for file in files if file.status == "edited"),
        "files_unchanged": sum(1 for file in files if file.status == "unchanged"),
        "files_dry_run": sum(1 for file in files if file.status == "dry_run"),
        "pages_original_total": sum(file.pages_original for file in files),
        "pages_removed_total": sum(file.pages_removed for file in files),
        "pages_output_total": sum(file.pages_output for file in files),
        "removed_pages_total": sum(file.pages_removed for file in files),
        "structural_empty_pages": 0,
        "render_empty_pages": 0,
        "both_empty_pages": 0,
        "pypdf_warnings_total": 0,
    }
    for file_result in files:
        totals["structural_empty_pages"] += file_result.decisions_summary.get(
            "structural_empty_pages",
            0,
        )
        totals["render_empty_pages"] += file_result.decisions_summary.get(
            "render_empty_pages",
            0,
        )
        totals["both_empty_pages"] += file_result.decisions_summary.get("both_empty_pages", 0)
        totals["pypdf_warnings_total"] += file_result.pypdf_warnings_count
    return totals


def _timestamp_for_filename(timestamp_local: str) -> str:
    return datetime.fromisoformat(timestamp_local).strftime("%Y%m%d_%H%M%S")


def _json_text(run_result: RunResult) -> str:
    import json

    return json.dumps(run_result_to_dict(run_result), indent=2, sort_keys=True) + "\n"


def _text_report(run_result: RunResult) -> str:
    lines = [
        "PDFEditor Run Report",
        "",
        f"Timestamp (local): {run_result.timestamp_local}",
        f"Timestamp (UTC):   {run_result.timestamp_utc}",
        f"User:              {run_result.user}",
        f"Host:              {run_result.host}",
        f"Python:            {run_result.python_version}",
        f"pypdf:             {run_result.pypdf_version}",
        f"pypdfium2:         {run_result.pypdfium2_version or 'not installed'}",
        "",
        "Config:",
        f"  path={run_result.config.path}",
        f"  out={run_result.config.out}",
        f"  report_dir={run_result.config.report_dir}",
        f"  mode={run_result.config.mode}",
        f"  effective_mode={run_result.config.effective_mode}",
        f"  render_dpi={run_result.config.render_dpi}",
        f"  ink_threshold={run_result.config.ink_threshold}",
        f"  background={run_result.config.background}",
        f"  effective_background={run_result.config.effective_background}",
        f"  render_sample_margin={list(run_result.config.render_sample_margin)}",
        f"  white_threshold={run_result.config.white_threshold}",
        f"  recursive={run_result.config.recursive}",
        f"  write_when_unchanged={run_result.config.write_when_unchanged}",
        f"  treat_annotations_as_empty={run_result.config.treat_annotations_as_empty}",
        f"  dry_run={run_result.config.dry_run}",
        f"  debug_structural={run_result.config.debug_structural}",
        f"  debug_pypdf_xref={run_result.config.debug_pypdf_xref}",
        f"  strict_xref={run_result.config.strict_xref}",
        f"  debug_render={run_result.config.debug_render}",
        f"  verbose={run_result.config.verbose}",
        "",
        "Detection Summary:",
        f"  structural_empty_pages={run_result.totals.get('structural_empty_pages', 0)}",
        f"  render_empty_pages={run_result.totals.get('render_empty_pages', 0)}",
        f"  both_empty_pages={run_result.totals.get('both_empty_pages', 0)}",
        f"  removed_pages_total={run_result.totals.get('removed_pages_total', 0)}",
        "",
        "Totals:",
    ]

    for key, value in run_result.totals.items():
        lines.append(f"  {key}={value}")

    if run_result.warnings:
        lines.extend(["", "Run warnings:"])
        lines.extend(f"  - {warning}" for warning in run_result.warnings)

    if run_result.errors:
        lines.extend(["", "Run errors:"])
        lines.extend(f"  - {error}" for error in run_result.errors)

    lines.extend(["", "Files:", _file_table(run_result.files)])

    for file_result in run_result.files:
        lines.extend(
            [
                "",
                f"[{file_result.status}] {file_result.input_path}",
                f"  output={file_result.output_path or '-'}",
                f"  pages_original={file_result.pages_original}",
                f"  pages_removed={file_result.pages_removed}",
                f"  pages_output={file_result.pages_output}",
                f"  timings={file_result.timings}",
                f"  decisions_summary={file_result.decisions_summary}",
                f"  pypdf_warnings_count={file_result.pypdf_warnings_count}",
            ]
        )
        if file_result.structural_debug_path:
            lines.append(f"  structural_debug={file_result.structural_debug_path}")
        if file_result.pypdf_warnings_path:
            lines.append(f"  pypdf_warnings_debug={file_result.pypdf_warnings_path}")
        if file_result.render_debug_path:
            lines.append(f"  render_debug={file_result.render_debug_path}")
        if file_result.warnings:
            lines.extend(f"  warning: {warning}" for warning in file_result.warnings)
        if file_result.errors:
            lines.extend(f"  error: {error}" for error in file_result.errors)

    return "\n".join(lines) + "\n"


def _file_table(files: list[FileResult]) -> str:
    if not files:
        return "status   removed   output   input\n(no PDF files found)"

    header = f"{'status':<10} {'removed':>7} {'output':>7} input"
    rows = [
        f"{file.status:<10} {file.pages_removed:>7} {file.pages_output:>7} {file.input_path}"
        for file in files
    ]
    return "\n".join([header, *rows])


def _serialize_value(value: Any) -> JSONValue:
    if is_dataclass(value):
        return {
            str(key): _serialize_value(item)
            for key, item in asdict(value).items()
        }
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {
            str(key): _serialize_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, tuple):
        return [_serialize_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
