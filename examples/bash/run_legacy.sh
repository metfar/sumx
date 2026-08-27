#!/bin/bash
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")/.." && pwd)
exec sumx --line-continuation semicolon --run "$here/legacy_continuation.prg"
