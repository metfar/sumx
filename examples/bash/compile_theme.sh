#!/bin/bash
set -e
THEME="${1:-Ralesk's MC}"
OUT="${TMPDIR:-/tmp}/sumx-theme-example.py"
sumx --theme "$THEME" --compile examples/window.prg -o "$OUT"
grep -E 'Compile-time theme|PROGRAM_THEME_(NAME|DATA)' "$OUT" | head -3
printf 'Generated: %s\n' "$OUT"
