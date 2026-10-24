#!/usr/bin/env python3
import glob, json, re, sys

pattern = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE
)

files = (
    glob.glob('*.html') +
    glob.glob('areas/*.html') +
    glob.glob('areas/**/*.html') +
    glob.glob('music-guides/*.html') +
    glob.glob('compare/*.html') +
    glob.glob('barbershop-grams/*.html') +
    glob.glob('destinations/*.html') +
    glob.glob('destinations/**/*.html')
)

errors = 0
for filepath in sorted(files):
    with open(filepath, encoding='utf-8') as f:
        content = f.read()
    for m in pattern.finditer(content):
        try:
            json.loads(m.group(1))
        except json.JSONDecodeError as e:
            print(f'INVALID JSON-LD in {filepath}: {e}')
            errors += 1

if errors:
    print(f'\n{errors} invalid JSON-LD block(s) found. Fix before deploying.')
    sys.exit(1)
else:
    print(f'JSON-LD valid in {len(files)} files checked.')
