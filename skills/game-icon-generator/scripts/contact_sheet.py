#!/usr/bin/env python3
"""Put all PNG icons from a folder on one sheet, so a whole set can be checked at a glance.

    python contact_sheet.py icons/ -o sheet.png [--cell 200] [--cols 6] [--width 1280 --height 720]

With --width and --height the sheet is exactly that size (handy for a 16:9 preview).
"""
import argparse
from pathlib import Path

from PIL import Image


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("-o", "--out", default="sheet.png")
    ap.add_argument("--cell", type=int, default=200, help="cell size in pixels")
    ap.add_argument("--cols", type=int, default=6)
    ap.add_argument("--width", type=int)
    ap.add_argument("--height", type=int)
    ap.add_argument("--background", default="#3c4260", help="background color")
    a = ap.parse_args()

    files = sorted(Path(a.folder).glob("*.png"))
    if not files:
        raise SystemExit("no PNG files found")
    cols = min(a.cols, len(files))
    rows = (len(files) + cols - 1) // cols
    width = a.width or cols * a.cell
    height = a.height or rows * a.cell
    cell = min(width // cols, height // rows)
    sheet = Image.new("RGBA", (width, height), a.background)
    x0, y0 = (width - cols * cell) // 2, (height - rows * cell) // 2
    pad = max(4, cell // 20)
    for i, f in enumerate(files):
        icon = Image.open(f).convert("RGBA").resize((cell - 2 * pad, cell - 2 * pad), Image.LANCZOS)
        sheet.alpha_composite(icon, (x0 + (i % cols) * cell + pad, y0 + (i // cols) * cell + pad))
    sheet.convert("RGB").save(a.out)
    print(a.out, sheet.size)


if __name__ == "__main__":
    main()
