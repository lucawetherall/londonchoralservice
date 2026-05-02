#!/usr/bin/env bash
# Build script for The London Choral Service website
# Concatenates CSS source files and inlines them into HTML pages

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CSS_DIR="$SCRIPT_DIR/css"

echo "Building CSS..."

cat \
  "$CSS_DIR/tokens.css" \
  "$CSS_DIR/base.css" \
  "$CSS_DIR/layout.css" \
  "$CSS_DIR/components.css" \
  "$CSS_DIR/pages.css" \
  > "$CSS_DIR/style.css"

echo "Created css/style.css ($(wc -c < "$CSS_DIR/style.css") bytes)"

echo "Inlining CSS into HTML files..."

count=0
for file in $(find "$SCRIPT_DIR" -name '*.html' -not -path '*/.git/*'); do
  if grep -q '<link rel="stylesheet" href=.*style\.css">' "$file"; then
    awk -v css="$CSS_DIR/style.css" '
      /<link rel="stylesheet" href=.*style\.css">/ {
        print "  <style>"
        while ((getline line < css) > 0) print "    " line
        close(css)
        print "  </style>"
        next
      }
      { print }
    ' "$file" > "$file.tmp" && mv "$file.tmp" "$file"
    count=$((count + 1))
  fi
done

echo "Inlined CSS into $count HTML files"

echo "Validating JSON-LD..."
errors=0
for file in $(find "$SCRIPT_DIR" -name '*.html' -not -path '*/.git/*'); do
  if grep -q 'application/ld+json' "$file"; then
    if ! python3 - "$file" <<'PY'
import re, json, sys
path = sys.argv[1]
with open(path) as fh:
    html = fh.read()
for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL):
    try:
        json.loads(m.group(1))
    except json.JSONDecodeError as e:
        print(f"INVALID: {path} - {e}", file=sys.stderr)
        sys.exit(1)
PY
    then
      errors=$((errors + 1))
    fi
  fi
done
if [ "$errors" -gt 0 ]; then
  echo "ERROR: $errors files have invalid JSON-LD"
  exit 1
fi
echo "All JSON-LD valid"

echo "Done."
