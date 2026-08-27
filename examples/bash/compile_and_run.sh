#!/bin/bash
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")/.." && pwd)
out=${TMPDIR:-/tmp}/sumx-conditionals-$$.py
trap 'rm -f -- "$out"' EXIT
sumx --compile "$here/conditionals.prg" --output "$out"
"$out"
