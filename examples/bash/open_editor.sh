#!/bin/bash
set -e

# Open a source file in the full-screen sumX editor/IDE.
# F9 opens File/Edit/Search/Run/Debug/Options/Help; F10 exits.
exec sumx "${1:-examples/hello.prg}"
