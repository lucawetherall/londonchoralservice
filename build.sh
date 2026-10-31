#!/usr/bin/env bash
# Build script for The London Choral Service website
# 1) Concatenates CSS source files
# 2) Populates HTML partials between @include-start / @include-end markers
# 3) Inlines each page's critical CSS and links the full bundle (scripts/inline_css.py)
# 4) Generates sitemap.xml + data/page-dates.json and sitemap-video.xml, and syncs article dates
# 5) Generates llms-full.txt and runs the validators
# 6) Checks the deploy allowlist: everything the pages use will be served,
#    nothing internal will (scripts/stage_site.py)

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
# Hidden top-level dirs (.git, .venv, .claude/worktrees, .superpowers) and graphify-out/ are never site content.
for file in $(find "$SCRIPT_DIR" -name '*.html' -not -path "$SCRIPT_DIR/.*" -not -path "$SCRIPT_DIR/graphify-out/*" -not -path '*/partials/*'); do
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

# Python for the generators and validators: $LCS_PYTHON if set, else the repo's
# .venv (it has PyYAML, see scripts/requirements.txt), also when building from a
# worktree, else python3.
PY="${LCS_PYTHON:-}"
if [ -z "$PY" ]; then
  PY=python3
  MAIN_CHECKOUT="$( (git rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true) | sed 's#/\.git$##')"
  for candidate in ".venv/bin/python" "$MAIN_CHECKOUT/.venv/bin/python"; do
    if [ -x "$candidate" ]; then PY="$candidate"; break; fi
  done
fi

echo "Inlining critical CSS into HTML files..."
# Each page inlines only the rules its first screen can use and loads css/style.css
# without blocking (preload, then stylesheet; <noscript> fallback). The block between
# <!-- @css-start … --> and <!-- @css-end --> is generated: never hand-edit it.
"$PY" scripts/inline_css.py

echo "Generating sitemap.xml from page content..."
"$PY" scripts/generate_sitemap.py

echo "Generating sitemap-video.xml (VideoObject JSON-LD), sitemap-images.xml (film stills) and sitemap_index.xml..."
"$PY" scripts/generate_video_sitemap.py

echo "Synchronising article dates..."
"$PY" scripts/sync_dates.py

echo "Generating llms-full.txt..."
"$PY" scripts/generate_llms_full.py

echo "Validating JSON-LD..."
"$PY" validate_jsonld.py

echo "Validating competitor claims..."
"$PY" validate_competitor_claims.py

echo "Validating house claims..."
"$PY" validate_house_claims.py

echo "Checking the deploy allowlist..."
"$PY" scripts/stage_site.py

# Advisory only: says whether graphify-out/ is behind the repo. Never fails the build.
"$PY" scripts/refresh_graph.py --check || echo "graph: check failed (ignored)"

echo "Done."
