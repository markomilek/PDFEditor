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
* verifies the default behavior for empty, annotation-only, text, footer-text, and whitespace-only pages
* verifies that annotation-only pages become non-empty when annotation handling is disabled

Expected behavior captured by the test matrix:

* structurally empty pages should be treated as empty
* annotation-only pages should be treated as empty by default
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

## Test Support Files

### `pdf_factory.py`

Deterministic PDF fixture factory built with `pypdf`.

Current capabilities:

* create truly empty pages
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
