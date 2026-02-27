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

Future-facing empty-page detection matrix.

Current coverage:

* defines expected outcomes for synthetic PDFs generated with `tests/pdf_factory.py`
* documents the intended default policy from `DECISIONS.md`
* is currently marked `xfail` because empty-page detection is not implemented yet

Expected behavior captured by the test matrix:

* structurally empty pages should be treated as empty
* annotation-only pages should be treated as empty by default
* pages containing page-number text should not be treated as empty
* whitespace-only content streams should be treated as empty

### `test_bookmark_drop.py`

Future-facing bookmark/outline rewrite behavior test.

Current coverage:

* generates a PDF with three pages
* creates a bookmark targeting a page that is expected to be removed later
* defines the expected post-rewrite behavior
* is currently marked `xfail` because rewrite logic is not implemented yet

Expected behavior captured by the test:

* when a referenced page is removed, the bookmark should be dropped
* the rewritten PDF should retain only the remaining pages

### `test_rewrite_behavior.py`

Future-facing rewrite behavior test for page removal.

Current coverage:

* generates a simple PDF with a removable middle page
* documents the expected output naming convention
* is currently marked `xfail` because rewrite logic is not implemented yet

Expected behavior captured by the test:

* rewritten output should use the `.edited.pdf` suffix
* removing one page should reduce the output page count by one

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
