#!/bin/bash
set -eu

CONFIG="${TMPDIR:-/tmp}/sumx-classroom-config.json"
rm -f "$CONFIG"

printf '%s\n' 'Available themes:'
sumx --list-themes

printf '\n%s\n' 'Open with a per-session theme and a separate classroom config:'
sumx --config "$CONFIG" --theme ZX examples/hello.prg
