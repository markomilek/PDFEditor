# UAT

This directory is reserved for manual user acceptance testing with real PDF files.

## Layout

Place input PDFs in `uat/input/`.

Expect generated PDFs in `uat/output/`.

Expect generated run reports in `uat/reports/`.

`uat/output/` and `uat/reports/` are safe to delete and regenerate.

## Planned Interface

Run the planned CLI interface from the repository root:

```bash
pdfeditor --path uat/input --out uat/output --report-dir uat/reports
```

These flags are not implemented yet. The command above documents the intended UAT workflow.

## Suggested Test PDFs

Include representative real-world samples such as:

* blank pages with no page number
* blank pages with page numbers rendered as text
* annotation-only pages
* mixed documents containing both empty and non-empty pages
* documents with bookmarks pointing to blank pages
