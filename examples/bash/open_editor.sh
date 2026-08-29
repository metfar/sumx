#!/bin/bash
set -e

# Open a source file in the full-screen sumX editor/IDE.
# F5 toggles Run/Stop; F6 moves between Editor and Output/Command.
# Ctrl+F6 compiles to Python; F9 opens the menu; F10 exits.
exec sumx "${1:-examples/hello.prg}"
