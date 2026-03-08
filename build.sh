#!/usr/bin/env bash
# Build script for The London Choral Service website
# Concatenates CSS source files into a single stylesheet

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
echo "Done."
