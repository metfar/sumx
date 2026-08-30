#!/bin/bash
set -e

# Open a source file in the full-screen sumX editor/IDE.
# F5 toggles Run/Stop; F6 cycles Code -> Output -> Command.
# F11 maximizes/restores the active window; Ctrl+F4 closes it.
# The Window menu reopens default windows; Ctrl+F6 compiles to Python.
# F9 opens the menu; F10 exits.
exec sumx "${1:-examples/hello.prg}"
