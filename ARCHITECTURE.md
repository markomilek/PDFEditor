# ARCHITECTURE.md

## System Architecture Overview

This document defines the authoritative structure, system boundaries, invariants, and responsibilities of **PDFEditor**.

It is the primary technical reference for both human developers and AI agents.

---

# 1. System Intent

**PDFEditor** is a Python command-line utility that:

1. Scans the current working directory for PDF files
2. Identifies empty pages using configurable heuristics
3. Produces a new PDF with empty pages removed
4. Applies safe structural corrections (e.g., drops bookmarks pointing to removed pages)
5. Generates comprehensive run reports

The system prioritizes:

* Non-destructive behavior
* Conservative defaults
* Enterprise-safe licensing
* Deterministic and testable execution

---

# 2. High-Level Processing Flow

For each `*.pdf` file found in the working directory:

## Step 1 — Open & Validate

* Attempt to open with `pypdf`
* Detect encryption
* Detect corruption or unreadable structures
* Record validation outcome

If unreadable or encrypted (without password support), skip and log.

---

## Step 2 — Analyze Pages

For each page:

* Apply configured empty-page detector
* Produce structured decision:

  * `is_empty: bool`
  * `reason: str`
  * `details: dict`

The result is a full page-level analysis plan.

---

## Step 3 — Build Edit Plan

From page analysis:

* Determine pages to retain
* Determine pages to remove
* Identify bookmarks/outlines/destinations that reference removed pages
* Prepare correction plan

Default correction policy:

* Drop references to removed pages

---

## Step 4 — Write Edited PDF

If at least one page is removed:

* Create new file:

```
<original_filename>.edited.pdf
```

* Copy retained pages in original order
* Apply bookmark/destination drop policy
* Preserve document metadata when possible

If no pages are removed:

* Do not write output (default behavior)
* Record "unchanged" status in report

---

## Step 5 — Write Run Reports

Every execution produces:

* `run_report_<timestamp>.json`
* `run_report_<timestamp>.txt`

Reports include:

* Timestamp (local and UTC)
* Username
* Hostname
* Python version
* `pypdf` version
* Per-file processing results
* Errors and warnings
* Page removal statistics

Reports are written to the working directory.

---

# 3. Module Responsibilities

Recommended package layout:

```
PDFEditor/
│
├── src/
│   └── pdfeditor/
│       ├── __init__.py
│       ├── cli.py
│       ├── processor.py
│       ├── detect_empty.py
│       ├── rewrite.py
│       ├── reporting.py
│       └── models.py
│
├── tests/
│
├── AGENTS.md
├── ARCHITECTURE.md
├── DECISIONS.md
└── pyproject.toml
```

---

## 3.1 cli.py

Responsibilities:

* Parse CLI arguments
* Discover PDFs in working directory
* Invoke processing pipeline
* Handle exit codes
* Aggregate run-level report

Must not contain business logic.

---

## 3.2 processor.py

Responsibilities:

* Orchestrate processing of a single PDF
* Invoke detectors
* Build edit plan
* Call rewrite logic
* Return structured file result object

---

## 3.3 detect_empty.py

Responsibilities:

* Implement empty-page detection logic
* Provide pluggable detection modes
* Default mode: conservative structural detection

Detection functions must:

* Be pure
* Not modify the PDF
* Return structured decision objects

---

## 3.4 rewrite.py

Responsibilities:

* Create edited PDF
* Copy retained pages
* Drop bookmarks/destinations referencing removed pages
* Preserve metadata when possible

Must not implement detection logic.

---

## 3.5 reporting.py

Responsibilities:

* Define JSON report schema
* Generate human-readable report
* Capture environment metadata
* Serialize per-file results

Reports must remain stable and structured.

---

## 3.6 models.py (Optional but Recommended)

Defines typed dataclasses for:

* Run configuration
* Page decision
* File processing result
* Warning/error records

This improves clarity and testability.

---

# 4. Invariants and Constraints

The following must always hold:

* Original PDFs are never modified
* Output files use suffix:

```
.edited.pdf
```

* Bookmark/destination correction policy is **drop**
* Pages containing only annotations are treated as empty by default
* All runs produce JSON and text reports
* All dependencies must be permissively licensed
* No external network calls

---

# 5. Configurability

The system must allow configuration via CLI flags.

Initial configuration options:

* Empty detection mode:

  * `structural` (default)

* Annotation handling:

  * `--treat-annotations-as-empty` (default: true)

* Output behavior:

  * `--write-when-unchanged` (default: false)

* Directory behavior:

  * Default: current directory
  * Optional future flag: `--recursive`

Future enhancements must preserve backward compatibility.

---

# 6. Explicit Non-Designs

The system does NOT implement:

* A GUI
* Rendering-based pixel detection
* In-place editing
* Telemetry or remote logging
* Non-permissive PDF libraries

---

# 7. Error Handling Philosophy

Errors are:

* Logged
* Associated with specific files
* Reported without halting processing of other files

Fatal errors should only occur for:

* Invalid CLI usage
* Environment-level failure

Per-file failures must not terminate the entire run.
