#!/bin/bash
set -e
HERE="$(cd "$(dirname "$0")/.." && pwd)"
exec sumx --run "$HERE/interactive_runtime.prg" "$@"
