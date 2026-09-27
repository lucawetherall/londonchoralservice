#!/usr/bin/env python3
"""The register generators must reproduce the live register pages byte for byte.

The destination country pages, the destinations hub and planners-and-venues.html
are generated (scripts/content_*.py via gen_country_pages.py, gen_destinations_index.py,
gen_planners_page.py). A hand edit to one of those pages that is not carried back
into its generator is lost the next time anyone regenerates. This test copies the
repo, reruns every generator and ./build.sh, and fails on any difference.

Stdlib only; takes about ten seconds. Run with: python3 tests/test_register_generators.py
"""
import filecmp
import glob
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERATORS = ['content_europe_a', 'content_europe_b', 'content_europe_c', 'content_americas',
              'content_indian_ocean', 'gen_destinations_index', 'gen_planners_page']


def main():
    tmp = tempfile.mkdtemp()
    work = os.path.join(tmp, 'site')
    try:
        shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns('.git', '__pycache__', '.venv', 'node_modules'))
        for g in GENERATORS:
            subprocess.run([sys.executable, f'scripts/{g}.py'], cwd=work, check=True, capture_output=True)
        subprocess.run(['./build.sh'], cwd=work, check=True, capture_output=True)
        pages = sorted(glob.glob('destinations/*.html', root_dir=ROOT)) + ['planners-and-venues.html']
        drift = [p for p in pages
                 if not filecmp.cmp(os.path.join(ROOT, p), os.path.join(work, p), shallow=False)]
    finally:
        shutil.rmtree(tmp)
    for p in drift:
        print(f'FAIL {p}: regenerating it changes the page. Carry the hand edit into its generator.')
    print(f'\n{len(drift)} of {len(pages)} register pages drift from their generators')
    return 1 if drift else 0


if __name__ == '__main__':
    sys.exit(main())
