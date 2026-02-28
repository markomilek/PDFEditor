# UAT

This directory is reserved for manual user acceptance testing with real PDF files.

## Layout

Place input PDFs in `uat/input/`.

Expect generated PDFs in `uat/output/`.

Expect generated run reports in `uat/reports/`.

`uat/output/` and `uat/reports/` are safe to delete and regenerate.

## CLI

Run the CLI from the repository root:

```bash
pdfeditor --path uat/input --out uat/output --report-dir uat/reports
```

### Render Mode

Optional rendering-based detection is available via:

```bash
pdfeditor --mode both --path uat/input --out uat/output --report-dir uat/reports
```

`render` and `both` require `pypdfium2`. If it is unavailable, `render` fails and `both` falls back to structural-only detection.

`ink_threshold` is the fraction of rendered pixels that must differ from the assumed background for a page to count as non-empty.

Printed page numbers inside PDF content are not renumbered after page removal.

## Suggested Test PDFs

Include representative real-world samples such as:

* blank pages with no page number
* blank pages with page numbers rendered as text
* annotation-only pages
* mixed documents containing both empty and non-empty pages
* documents with bookmarks pointing to blank pages
