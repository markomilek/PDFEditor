"""Typed models for PDFEditor run configuration and results."""

from __future__ import annotations

from dataclasses import dataclass, field

JSONScalar = str | int | float | bool | None
JSONValue = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]


@dataclass(frozen=True)
class RunConfig:
    """Configuration for a single CLI run."""

    path: str
    out: str
    report_dir: str
    recursive: bool
    write_when_unchanged: bool
    treat_annotations_as_empty: bool
    dry_run: bool
    verbose: bool


@dataclass(frozen=True)
class PageDecision:
    """A structured empty-page decision for one page."""

    page_index: int
    is_empty: bool
    reason: str
    details: dict[str, JSONValue]


@dataclass(frozen=True)
class RewriteResult:
    """Result details for a rewritten PDF."""

    output_path: str
    pages_output: int
    outlines_copied: int
    outlines_dropped: int
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FileResult:
    """Processing result for a single PDF."""

    input_path: str
    output_path: str | None
    status: str
    pages_original: int
    pages_removed: int
    pages_output: int
    decisions_summary: dict[str, int]
    page_decisions: list[PageDecision]
    warnings: list[str]
    errors: list[str]
    timings: dict[str, float]


@dataclass(frozen=True)
class RunResult:
    """Aggregated result for a full CLI run."""

    timestamp_local: str
    timestamp_utc: str
    user: str
    host: str
    python_version: str
    pypdf_version: str
    config: RunConfig
    files: list[FileResult]
    totals: dict[str, int]
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
