# Tests

This directory contains the automated test scaffold for `PDFEditor`.

The test suite is expected to grow as implementation work is added. Update this file whenever new test modules, fixtures, or testing conventions are introduced.

## Current Test Files

### `test_smoke.py`

Minimal package smoke test.

Current coverage:

* imports `pdfeditor`
* verifies that `pdfeditor.__version__` exists

Purpose:

* confirms the package scaffold imports correctly
* catches basic packaging or import regressions

### `test_detection_matrix.py`

Structural empty-page detection matrix.

Current coverage:

* defines expected outcomes for synthetic PDFs generated with `tests/pdf_factory.py`
* documents the intended default policy from `DECISIONS.md`
* verifies the default behavior for empty, annotation-only, text, footer-text, whitespace-only, and state-ops-only pages
* verifies that blank pages with carried font resources are still treated as empty when they contain no paint operators
* verifies that invisible paint techniques such as `Tr 3` are treated as empty in structural mode
* verifies that annotation-only pages become non-empty when annotation handling is disabled

Expected behavior captured by the test matrix:

* structurally empty pages should be treated as empty
* annotation-only pages should be treated as empty by default
* font resources alone do not make a page non-empty
* state/layout operators alone do not make a page non-empty
* non-visible painting alone does not make a page non-empty
* pages containing page-number text should not be treated as empty
* whitespace-only content streams should be treated as empty

### `test_bookmark_drop.py`

Bookmark/outline rewrite behavior test.

Current coverage:

* generates a PDF with three pages
* creates a bookmark targeting a page that is expected to be removed later
* verifies the expected post-rewrite behavior

Expected behavior captured by the test:

* when a referenced page is removed, the bookmark should be dropped
* the rewritten PDF should retain only the remaining pages

### `test_rewrite_behavior.py`

Rewrite behavior tests for page removal and output naming.

Current coverage:

* generates a simple PDF with a removable middle page
* verifies the output naming convention
* verifies collision-safe numeric suffixing when an edited output already exists

Expected behavior captured by the test:

* rewritten output should use the `.edited.pdf` suffix
* removing one page should reduce the output page count by one

### `test_cli_end_to_end.py`

End-to-end CLI and reporting test.

Current coverage:

* runs the CLI against a temporary input directory
* verifies that an edited PDF is written
* verifies that JSON and text reports are always written
* checks basic totals in the generated JSON report

### `test_cli_modes.py`

CLI mode and optional-render fallback tests.

Current coverage:

* verifies render-related CLI argument parsing
* verifies `--mode both` falls back to structural-only when `pypdfium2` is unavailable
* verifies `--mode render` exits with code `2` and writes reports when `pypdfium2` is unavailable

### `test_cli_render_margin_parse.py`

CLI parsing coverage for render body sampling margins.

Current coverage:

* verifies `--render-sample-margin` parses `TOP,LEFT,RIGHT,BOTTOM` values in inches
* verifies optional spaces are accepted
* verifies wrong counts fail with exit code `2`
* verifies negative values fail with exit code `2`

### `test_cli_page_number_parse.py`

CLI parsing coverage for page-number stamping options.

Current coverage:

* verifies `--stamp-page-numbers` requires `--pagenum-box`
* verifies `--stamp-page-numbers-force` requires `--stamp-page-numbers`
* verifies `--stamp-page-numbers-force` parses correctly when stamping is enabled
* verifies `--pagenum-box` parses `x,y,w,h` values in inches
* verifies invalid box formats fail with exit code `2`
* verifies negative box values fail with exit code `2`

### `test_wordlike_blank_page.py`

Regression test for Word-like blank pages that still carry font resources.

Current coverage:

* builds a two-page PDF where page 1 is blank but carries font resources copied from the text page
* verifies that page 1 is still classified as empty even when it has state/layout operators
* verifies that the visible-text page remains non-empty

### `test_invisible_paint_detection.py`

Regression test for structurally invisible paint operations.

Current coverage:

* verifies that text with `Tr 3` is treated as empty
* verifies that text with font size `0` is treated as empty
* verifies that text under zero-opacity `ExtGState` is treated as empty
* verifies that a normal visible text page remains non-empty

### `test_render_detection.py`

Optional render-detector tests.

Current coverage:

* skipped automatically when `pypdfium2` is not installed
* verifies that a rendered blank page is classified empty
* verifies that a rendered text page is classified non-empty

### `test_render_debug_output.py`

Optional render-debug artifact coverage.

Current coverage:

* skipped automatically when `pypdfium2` is not installed
* runs `process_pdf()` with render debugging enabled
* verifies that a separate render debug JSON artifact is written
* verifies that the artifact contains per-page render statistics, `white_threshold`, and `sample_margin_inches`

### `test_structural_debug_output.py`

Structural debug artifact coverage.

Current coverage:

* runs `process_pdf()` with structural debug enabled
* verifies that a separate structural debug JSON artifact is written
* verifies that the artifact contains per-page records and operator summaries
* ensures the debug path is carried back in the structured file result

### `test_pypdf_warning_capture.py`

Synthetic `pypdf` warning capture coverage.

Current coverage:

* verifies that warnings logged under the `pypdf` logger are captured into structured events
* verifies that captured events contain a message and stack trace
* verifies the strict helper raises when warnings are present

### `test_page_number_stamping.py`

Page-number stamping coverage.

Current coverage:

* verifies Roman numeral conversion and format token replacement
* conditionally verifies stamping adds visible footer ink when `pypdfium2` is available
* conditionally verifies the stamping guardrail skips pages where the configured box already contains real content
* conditionally verifies forced stamping bypasses the guardrail and records `stamped_forced`

## Test Support Files

### `pdf_factory.py`

Deterministic PDF fixture factory built with `pypdf`.

Current capabilities:

* create truly empty pages
* create visually blank pages that still contain font resources
* create pages with state/layout operators but no paint operators
* create pages with invisible text via `Tr 3`, zero font size, and zero-opacity `ExtGState`
* create pages with small text
* create footer page-number text pages
* create annotation-only pages
* create whitespace-only content stream pages
* create simple shape pages
* write generated PDFs to bytes or disk
* add simple outline entries

Purpose:

* keep PDF-based tests deterministic
* avoid dependence on external sample PDFs for unit and integration scaffolding

### `__init__.py`

Marks `tests/` as an importable package so shared helpers such as `pdf_factory.py` can be imported reliably by the test modules.

## Conventions

* Use deterministic fixtures.
* Do not modify real user PDFs.
* Prefer synthetic PDFs from `pdf_factory.py` for automated tests.
* Mark future-facing tests clearly when the production feature is intentionally not implemented yet.

## Structural Limitations

Structural mode now treats pages as empty when they contain only non-visible painting such as:

* text rendering mode `Tr 3`
* text with font size `0`
* paint operations under zero fill/stroke opacity

Structural mode still does not attempt:

* white-on-white detection
* hidden-behind-objects or z-order visibility analysis

## Render Mode

Render mode is optional and depends on `pypdfium2`.

Modes:

* `structural`: use only the structural detector
* `render`: use only the rendering detector
* `both`: remove a page if either detector marks it empty

If `pypdfium2` is unavailable:

* `render` fails with exit code `2`
* `both` falls back to structural-only and records a warning

Render sampling always uses a body region defined by `--render-sample-margin "TOP,LEFT,RIGHT,BOTTOM"` in inches.

* `0,0,0,0` samples the full page
* non-zero margins exclude headers, footers, or side gutters from the ink calculation
* if margins eliminate the entire sample area, render mode returns `invalid_sample_area` conservatively

## Structural Debugging

The CLI also supports `--debug-structural`.

When enabled:

* the structural detector emits a separate per-file JSON artifact in the report directory
* the main run report includes the path to that artifact
* each page record includes content-stream metadata, capped stream previews, and an operator summary derived from `pypdf` parsing

## pypdf Warning Debugging

The CLI also supports `--debug-pypdf-xref` and `--strict-xref`.

When enabled:

* `pypdf` warnings are captured into a separate per-file JSON artifact instead of being printed to the console
* `--strict-xref` treats any captured `pypdf` warning as a per-file failure

## Render Debugging

The CLI also supports `--debug-render`, `--white-threshold`, and `--render-sample-margin`.

When enabled:

* the render detector emits a separate per-file JSON artifact with per-page pixel statistics
* `white_threshold` controls how close to white a rendered pixel may be before it counts as background
* `render-sample-margin` defines the sampled body region in inches from the top, left, right, and bottom edges
* render debug tests are skipped automatically when `pypdfium2` is unavailable

## Page-Number Stamping

Page-number stamping is optional and depends on `pypdfium2`.

Current behavior:

* `--pagenum-box` uses `x,y,w,h` in inches from the bottom-left origin
* the configured box is covered with a filled rectangle before the corrected label is stamped
* the stamped label is centered in the box
* the guardrail uses the existing `ink_threshold`
* if the box already contains real content above the guardrail threshold, stamping is skipped for that page
* `--stamp-page-numbers-force` bypasses the guardrail and stamps anyway
