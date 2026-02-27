"""Command-line interface scaffold for PDFEditor."""

from __future__ import annotations

import argparse


def main() -> None:
    """Run the scaffold CLI."""
    parser = argparse.ArgumentParser(prog="pdfeditor")
    parser.parse_args()
    print("pdfeditor: scaffold created (no functionality yet)")
