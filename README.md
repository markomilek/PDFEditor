# PDFEditor

PDFEditor is a local, non-destructive command-line tool for identifying empty PDF pages, writing edited copies with those pages removed, and producing auditable run reports.

The project is designed for controlled enterprise use:

* local-only execution
* deterministic behavior
* no network calls, telemetry, or cloud uploads
* conservative defaults to reduce accidental content loss
* machine-readable and human-readable reporting for every run

## Purpose

PDFEditor helps teams process PDF collections where blank or effectively blank pages need to be removed without modifying the original files.

Typical enterprise use cases:

* preparing document sets for downstream review or archival
* cleaning generated PDFs that contain trailing or inserted blank pages
* validating documents during manual UAT with real customer or internal samples
* producing repeatable reports for audit and troubleshooting

## Current Functionality

The current implementation supports:

* scanning a directory for PDF files
* non-recursive processing by default, with optional recursive traversal
* ignoring files already ending in `.edited.pdf`
* structural empty-page detection
* rendering-based empty-page detection using `pypdfium2`
* combined mode where a page is treated as empty if either the structural detector or the render detector marks it empty
* non-destructive rewrite to a new file using the `.edited.pdf` suffix
* collision-safe output naming such as `.edited.1.pdf`, `.edited.2.pdf`, and so on
* dropping bookmarks, outlines, and named destinations that reference removed pages
* JSON and text run reports for every execution
* optional debug artifacts for:
  * structural analysis
  * render analysis
  * `pypdf` warning capture

## Safety Model

The tool is intentionally conservative.

Core safety rules:

* original PDFs are never overwritten
* edited output is always written to a new file using `.edited.pdf`
* if bookmark or outline references become invalid after page removal, those references are dropped rather than retargeted
* encrypted or unreadable PDFs are skipped and recorded in the report
* each run produces:
  * `run_report_<timestamp>.json`
  * `run_report_<timestamp>.txt`

## Detection Modes

### Structural Mode

Structural mode inspects PDF structure and content streams without rendering the page.

Current structural behavior includes:

* conservative empty-page classification
* annotation-only pages are treated as empty by default
* pages with only state/layout operators are treated as empty
* pages with only non-visible paint such as:
  * `Tr 3`
  * font size `0`
  * zero-opacity ExtGState
  are treated as empty
* pages with XObjects remain conservatively non-empty

### Render Mode

Render mode uses the packaged `pypdfium2` dependency installed with PDFEditor.

Render mode:

* renders each page to a bitmap
* measures visible ink inside a configurable body region
* treats near-white pixels as background using `white_threshold`
* treats a page as empty when sampled ink coverage is below `ink_threshold`

### Both Mode

In `--mode both`, a page is treated as empty if:

* the structural detector marks it empty, or
* the render detector marks it empty

## Installation

Preferred end-user installation:

```bash
pip3 install git+https://github.com/markomilek/PDFEditor.git
```

This installs `pdfeditor` together with its runtime dependencies, including `pypdfium2`.

Contributor installation from a local clone:

```bash
git clone https://github.com/markomilek/PDFEditor.git
cd PDFEditor
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
pip3 install -e .
```

Notes:

* the Git-based `pip3 install` command above is the preferred installation method for users
* the editable install workflow above is intended for contributors working from a local checkout
* `requirements.txt` is for contributor and local validation setup
* do not replace this workflow with Poetry, Hatch, or Pipenv
* the project uses `setuptools`
* editable install is recommended for local development and validation

## Command-Line Usage

Basic run:

```bash
pdfeditor --path . --out . --report-dir .
```

Common examples:

Process a directory structurally:

```bash
pdfeditor --path incoming_pdfs --out cleaned_pdfs --report-dir reports --mode structural
```

Use combined detection with full-page render sampling:

```bash
pdfeditor --path incoming_pdfs --out cleaned_pdfs --report-dir reports --mode both --render-sample-margin "0,0,0,0"
```

Ignore a 0.5 inch footer in render sampling:

```bash
pdfeditor --path incoming_pdfs --out cleaned_pdfs --report-dir reports --mode both --render-sample-margin "0,0,0,0.5"
```

Ignore header and footer in render sampling:

```bash
pdfeditor --path incoming_pdfs --out cleaned_pdfs --report-dir reports --mode both --render-sample-margin "0.5,0,0,0.75"
```

Perform a dry run:

```bash
pdfeditor --path incoming_pdfs --out cleaned_pdfs --report-dir reports --dry-run --verbose
```

Write unchanged files as copied outputs:

```bash
pdfeditor --path incoming_pdfs --out cleaned_pdfs --report-dir reports --write-when-unchanged
```

Enable structural, render, and `pypdf` warning debug artifacts:

```bash
pdfeditor --path uat/input --out uat/output --report-dir uat/reports --mode both --debug-structural --debug-render --debug-pypdf-xref --verbose
```

## CLI Options Summary

Important options:

* `--path PATH`
  Directory to scan for PDFs. Default: current directory.
* `--out PATH`
  Directory for edited PDFs. Default: same as `--path`.
* `--report-dir PATH`
  Directory for JSON and text reports. Default: same as `--path`.
* `--recursive`
  Scan subdirectories.
* `--mode {structural,render,both}`
  Detection mode. Default: `both`.
* `--write-when-unchanged`
  Write a copied output even when no pages are removed.
* `--treat-annotations-as-empty`
  Default: enabled.
* `--dry-run`
  Report planned changes without writing edited PDFs.
* `--verbose`
  Print per-file processing details.

Render-specific options:

* `--render-dpi INT`
  Render resolution. Default: `72`.
* `--ink-threshold FLOAT`
  Minimum non-background coverage required for a page to count as non-empty. Default: `1e-5`.
* `--white-threshold INT`
  A pixel is treated as white/background when its RGB values are at or above this threshold. Default: `240`.
* `--background {white,auto}`
  `auto` currently falls back to `white` with a warning.
* `--render-sample-margin "TOP,LEFT,RIGHT,BOTTOM"`
  Body sampling margins in inches. Default: `"0,0,0,0"`.

Debugging options:

* `--debug-structural`
  Write per-file structural debug JSON.
* `--debug-render`
  Write per-file render debug JSON.
* `--debug-pypdf-xref`
  Capture `pypdf` warnings into a JSON artifact instead of leaving them as console noise.
* `--strict-xref`
  Treat captured `pypdf` warnings as per-file failures.

Page-number correction options:

* `--stamp-page-numbers`
  Enable post-rewrite page-number correction.
* `--stamp-page-numbers-force`
  Force stamping even when the configured box already contains ink. Use with caution.
* `--pagenum-box "x,y,w,h"`
  Required when stamping is enabled. The box is measured in inches from the bottom-left corner of the page.
* `--pagenum-size FLOAT`
  Stamped font size in points. Default: `10`.
* `--pagenum-font {Helvetica,Times-Roman,Courier}`
  Stamped font family. Default: `Helvetica`.
* `--pagenum-format STRING`
  Supports `{page}`, `{roman}`, and `{ROMAN}`. Default: `{page}`.

## Reports and Debug Artifacts

Every execution writes:

* `run_report_<timestamp>.json`
* `run_report_<timestamp>.txt`

Run reports include:

* local and UTC timestamps
* username and hostname
* Python version
* `pypdf` version
* `pypdfium2` version
* run configuration
* per-file status
* pages removed and output counts
* warnings and errors

Optional debug artifacts:

* `structural_debug_<input_stem>_<timestamp>.json`
* `render_debug_<input_stem>_<timestamp>.json`
* `pypdf_warnings_<input_stem>_<timestamp>.json`

These artifacts are intended for troubleshooting difficult PDFs and validating detector behavior.

## Render Sampling Model

Render sampling always uses the page body region.

The body region is the page area remaining after excluding:

* top margin
* left margin
* right margin
* bottom margin

All margins are specified in inches via:

```bash
--render-sample-margin "TOP,LEFT,RIGHT,BOTTOM"
```

Examples:

* `0,0,0,0` samples the whole page
* `0,0,0,0.5` ignores a half-inch footer
* `0.5,0.25,0.25,0.75` ignores header, left gutter, right gutter, and footer

If the specified margins eliminate the whole sample area, render mode returns `invalid_sample_area` and treats the page as non-empty conservatively.

Threshold interaction:

* `white_threshold` controls which pixels still count as background
* `ink_threshold` controls how much sampled ink is required before the page becomes non-empty

## Page Number Correction (Stamping)

PDFEditor can optionally correct printed page numbers after page deletions by covering the configured footer or header number area and stamping a new centered label.

Behavior:

* stamping runs on the rewritten output pages
* the old page-number box is covered with a filled rectangle
* cover color is chosen automatically from rendered page pixels in that box
* the replacement label is centered in the box
* numbering follows final output order, starting at `1`

Supported format tokens:

* `{page}` for Arabic numerals
* `{roman}` for lowercase Roman numerals
* `{ROMAN}` for uppercase Roman numerals

Examples:

```bash
pdfeditor --path incoming_pdfs --out cleaned_pdfs --report-dir reports --stamp-page-numbers --pagenum-box "0.75,0.25,1.0,0.5"
pdfeditor --path incoming_pdfs --out cleaned_pdfs --report-dir reports --stamp-page-numbers --pagenum-box "0.75,0.25,1.0,0.5" --pagenum-format "Page {page}"
pdfeditor --path incoming_pdfs --out cleaned_pdfs --report-dir reports --stamp-page-numbers --pagenum-box "0.75,0.25,1.0,0.5" --pagenum-font Times-Roman --pagenum-size 11 --pagenum-format "{ROMAN}"
pdfeditor --path incoming_pdfs --out cleaned_pdfs --report-dir reports --stamp-page-numbers --stamp-page-numbers-force --pagenum-box "0.75,0.25,1.0,0.5"
```

Units and coordinate system:

* `pagenum-box` is `x,y,w,h`
* all values are inches
* origin is the page bottom-left corner

Guardrail:

* PDFEditor renders the configured page-number box and measures ink within it using the existing `ink_threshold`
* if the box already contains real content above the guardrail threshold, stamping is skipped for that page
* this avoids covering non-page-number content accidentally

Forced stamping:

* `--stamp-page-numbers-force` bypasses the guardrail and stamps every output page
* use this only when you are confident the configured box is reserved for page numbers
* forced stamping can overwrite real footer or header content

Caveats:

* stamping requires `pypdfium2`
* the tool does not rebuild tables of contents, figures, indexes, or internal printed references
* bookmark and outline correction policy remains drop-only for removed pages

## Testing

Run the automated test suite with:

```bash
venv/bin/pytest
```

The suite covers:

* package smoke testing
* structural empty-page detection matrix
* invisible paint behavior
* rewrite behavior and output naming
* bookmark drop policy
* CLI mode parsing and fallback behavior
* render detection
* structural debug artifact output
* render debug artifact output
* `pypdf` warning capture

Some render-related tests are skipped automatically if `pypdfium2` is not installed.

See [tests/README.md](/Users/markomilek/Coding/PDFEditor/tests/README.md) for the detailed test inventory.

## Validation and UAT

For manual validation with real PDFs, use the `uat/` area:

* `uat/input/` for input files
* `uat/output/` for generated edited PDFs
* `uat/reports/` for run reports and debug artifacts

Example UAT command:

```bash
pdfeditor --path uat/input --out uat/output --report-dir uat/reports --mode both --render-sample-margin "0,0,0,0" --verbose
```

For deeper troubleshooting:

```bash
pdfeditor --path uat/input --out uat/output --report-dir uat/reports --mode both --debug-structural --debug-render --debug-pypdf-xref --verbose
```

See [uat/README.md](/Users/markomilek/Coding/PDFEditor/uat/README.md) for UAT-specific guidance and file layout.

## Exit Codes

* `0`
  All files processed without failures.
* `2`
  One or more files failed, or a required render dependency was unavailable for the selected mode.

## Project Structure

High-level repository layout:

```text
.
├── src/pdfeditor/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── detect_empty.py
│   ├── detect_render.py
│   ├── models.py
│   ├── processor.py
│   ├── pypdf_debug.py
│   ├── reporting.py
│   └── rewrite.py
├── tests/
│   ├── README.md
│   ├── pdf_factory.py
│   └── test_*.py
├── uat/
│   ├── README.md
│   ├── input/
│   ├── output/
│   └── reports/
├── AGENTS.md
├── ARCHITECTURE.md
├── DECISIONS.md
├── LICENSE
├── pyproject.toml
└── requirements.txt
```

Module responsibilities:

* `cli.py`
  Argument parsing and run orchestration.
* `processor.py`
  Per-file processing pipeline.
* `detect_empty.py`
  Structural empty-page detection.
* `detect_render.py`
  Optional render-based empty-page detection.
* `rewrite.py`
  Edited PDF writing and reference dropping.
* `reporting.py`
  JSON and text report generation.
* `pypdf_debug.py`
  Structured capture of `pypdf` warnings.
* `models.py`
  Typed dataclasses for configuration and results.

## Enterprise Considerations

This project is intended to be suitable for enterprise review and internal tooling usage.

Relevant characteristics:

* permissive dependency posture
* no external services
* auditable output artifacts
* deterministic execution
* non-destructive file handling
* explicit failure recording
* conservative bookmark and destination handling

Operational recommendations:

* validate on representative documents before broad rollout
* review JSON reports in automated workflows
* use `--dry-run` for first-pass analysis
* enable debug artifacts only when troubleshooting, because they increase report volume

## Limitations

Current limitations include:

* no password support for encrypted PDFs
* no in-place editing
* no bookmark retargeting
* no printed page-number renumbering inside page content
* structural mode does not attempt white-on-white or z-order visibility analysis
* render mode depends on `pypdfium2`

## License

MIT. See [LICENSE](/Users/markomilek/Coding/PDFEditor/LICENSE).
