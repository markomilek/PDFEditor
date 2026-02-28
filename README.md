# PDFEditor

CLI tool for non-destructive PDF empty-page detection and rewrite reporting.

## Install

```bash
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
pip install -e .
```

## Run

```bash
pdfeditor
```

## Render Mode

Render mode measures rendered "ink" only inside the body region of each page.

The body region is defined by `--render-sample-margin "TOP,LEFT,RIGHT,BOTTOM"` where each value is in inches. The margins are excluded from the sampled area on each edge.

Examples:

```bash
pdfeditor --mode both --render-sample-margin "0,0,0,0"
pdfeditor --mode both --render-sample-margin "0,0,0,0.5"
pdfeditor --mode both --render-sample-margin "0.5,0,0,0.75"
```

Interpretation:

* `0,0,0,0`: sample the whole page
* `0,0,0,0.5`: ignore a 0.5" footer
* `0.5,0,0,0.75`: ignore a 0.5" header and a 0.75" footer

`white_threshold` controls how close to white a rendered pixel may be before it still counts as background. `ink_threshold` controls how much non-background coverage is required before a page counts as non-empty.
