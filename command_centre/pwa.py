"""The installable app: the web app manifest and its icons.

The icons are drawn here in pure Python (Pillow isn't in the venv): "LCS" in block letters, cream on the brand
red, as PNG files in static/icons/. `python -m command_centre.pwa` redraws them; tests/test_cc_pwa.py checks the
committed files match what this draws. Nothing is loaded from any other origin.
"""

import struct
import sys
import zlib
from pathlib import Path

ICONS = Path(__file__).resolve().parent / "static" / "icons"
NAME = "LCS Command Centre"
SHORT_NAME = "LCS"
THEME = "#8B3A3A"   # --accent in static/app.css (the site's brand red)
BACKGROUND = "#F7F3EE"  # --bg in static/app.css
INK = (0xF7, 0xF3, 0xEE)
FIELD = (0x8B, 0x3A, 0x3A)
# (file name, size in pixels, share of the width the letters take, manifest purpose)
SIZES = [("icon-180.png", 180, 0.62, None), ("icon-192.png", 192, 0.62, "any"), ("icon-512.png", 512, 0.62, "any"),
         ("icon-maskable-512.png", 512, 0.50, "maskable")]
GLYPHS = {  # 5 x 7 block letters
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
}
TEXT = "LCS"


def manifest():
    return {
        "id": "/",
        "name": NAME,
        "short_name": SHORT_NAME,
        "description": "The London Choral Service's private dashboard.",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": BACKGROUND,
        "theme_color": THEME,
        "lang": "en-GB",
        "icons": [{"src": f"/static/icons/{name}", "sizes": f"{size}x{size}", "type": "image/png",
                   **({"purpose": purpose} if purpose else {})}
                  for name, size, _, purpose in SIZES if name != "icon-180.png"],
    }


def pixels(size, share):
    """Rows of RGB tuples: the letters centred on the brand red."""
    cols = len(TEXT) * 5 + (len(TEXT) - 1)
    cell = max(1, int(size * share) // cols)
    width, height = cols * cell, 7 * cell
    left, top = (size - width) // 2, (size - height) // 2
    ink = set()
    for i, ch in enumerate(TEXT):
        for r, row in enumerate(GLYPHS[ch]):
            for c, bit in enumerate(row):
                if bit == "1":
                    ink.add((r, i * 6 + c))
    rows = []
    for y in range(size):
        row = []
        for x in range(size):
            gy, gx = (y - top) // cell, (x - left) // cell
            inside = top <= y < top + height and left <= x < left + width
            row.append(INK if inside and (gy, gx) in ink else FIELD)
        rows.append(row)
    return rows


def png(rows):
    """A minimal, deterministic RGB PNG."""
    height, width = len(rows), len(rows[0])
    raw = b"".join(b"\x00" + bytes(v for px in row for v in px) for row in rows)

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def icon_bytes():
    """{file name: PNG bytes} for every icon."""
    return {name: png(pixels(size, share)) for name, size, share, _ in SIZES}


def write_icons(folder=ICONS):
    folder.mkdir(parents=True, exist_ok=True)
    for name, body in icon_bytes().items():
        (folder / name).write_bytes(body)
    return sorted(icon_bytes())


if __name__ == "__main__":
    print("\n".join(write_icons()))
    sys.exit(0)
