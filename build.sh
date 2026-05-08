#!/usr/bin/env bash
# Build script for The London Choral Service website
# 1) Concatenates CSS source files
# 2) Populates HTML partials between @include-start / @include-end markers
# 3) Inlines the concatenated CSS into HTML files

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

echo "Populating HTML partials..."

include_count=0
for file in $(find "$SCRIPT_DIR" -name '*.html' -not -path '*/.git/*' -not -path '*/partials/*'); do
  if grep -q '@include-start' "$file"; then
    # Validate that every referenced partial exists; fail loudly if not.
    # Done in shell (not awk) so set -euo pipefail catches the failure cleanly.
    while IFS= read -r marker_line; do
      partial=$(echo "$marker_line" | sed -n 's/.*@include-start \([^ ]*\) -->.*/\1/p')
      partial_path="$SCRIPT_DIR/$partial"
      if [[ ! -f "$partial_path" ]]; then
        echo "build.sh: partial not found: $partial_path (referenced from $file)" >&2
        exit 1
      fi
    done < <(grep '@include-start' "$file")

    awk -v root="$SCRIPT_DIR" '
      /<!-- @include-start [^ ]+ -->/ {
        match($0, /@include-start [^ ]+/)
        # 15 = length("@include-start ")
        partial = substr($0, RSTART + 15, RLENGTH - 15)
        partial_path = root "/" partial
        print
        skipping = 1
        # Emit the partial contents
        while ((getline line < partial_path) > 0) print line
        close(partial_path)
        next
      }
      /<!-- @include-end [^ ]+ -->/ {
        skipping = 0
        print
        next
      }
      skipping == 1 { next }
      { print }
    ' "$file" > "$file.tmp" && mv "$file.tmp" "$file"
    include_count=$((include_count + 1))
  fi
done

echo "Populated partials in $include_count HTML files"

echo "Inlining CSS into HTML files..."

count=0
for file in $(find "$SCRIPT_DIR" -name '*.html' -not -path '*/.git/*' -not -path '*/partials/*'); do
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
python3 validate_jsonld.py

echo "Done."
