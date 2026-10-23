#!/usr/bin/env python3
"""Render the printable sheets in scripts/print/ to PDFs in assets/print/.

Uses headless Chrome (or the Playwright Chromium in ~/Library/Caches) to print
each source page at A4 with no header or footer. Run from the repo root:

    python3 scripts/print/render_pdf.py

then ./build.sh, and commit the PDF with its source.
"""
import glob
import os
import shutil
import subprocess
import sys

SHEETS = {
    'scripts/print/funeral-music-sheet.html': 'assets/print/funeral-music-sheet.pdf',
}

CANDIDATES = [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    *sorted(glob.glob(os.path.expanduser(
        '~/Library/Caches/ms-playwright/chromium-*/chrome-mac*/Chromium.app/Contents/MacOS/Chromium')),
        reverse=True),
    shutil.which('chromium') or '',
    shutil.which('google-chrome') or '',
]


def chrome():
    for path in CANDIDATES:
        if path and os.path.exists(path):
            return path
    sys.exit('No Chrome or Chromium found; install Google Chrome or Playwright Chromium.')


def main():
    binary = chrome()
    for src, out in SHEETS.items():
        os.makedirs(os.path.dirname(out), exist_ok=True)
        subprocess.run([
            binary, '--headless', '--disable-gpu', '--no-pdf-header-footer',
            '--allow-file-access-from-files', '--run-all-compositor-stages-before-draw',
            '--virtual-time-budget=5000', f'--print-to-pdf={os.path.abspath(out)}',
            'file://' + os.path.abspath(src),
        ], check=True, capture_output=True)
        print(f'{src} -> {out} ({os.path.getsize(out):,} bytes)')


if __name__ == '__main__':
    main()
