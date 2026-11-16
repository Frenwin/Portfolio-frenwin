"""Render each page of the Power BI PDF export to a PNG for the README.

Usage:
    python tools/pdf_to_png.py docs/dashboard.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path

import pypdfium2 as pdfium

NAMES = ["page-1-overview.png", "page-2-drilldown.png"]


def main() -> None:
    pdf_path = Path(sys.argv[1])
    pdf = pdfium.PdfDocument(str(pdf_path))
    for i, page in enumerate(pdf):
        name = NAMES[i] if i < len(NAMES) else f"page-{i + 1}.png"
        target = pdf_path.parent / name
        page.render(scale=2).to_pil().save(target, optimize=True)
        print(f"{target} ({page.get_width():.0f} x {page.get_height():.0f} pt)")


if __name__ == "__main__":
    main()
