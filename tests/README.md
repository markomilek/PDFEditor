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
