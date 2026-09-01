#!/bin/bash
set -e

# Open a source file in the full-screen sumX editor/IDE.
# F2 / Alt+P opens Program Map.
# F5 / Ctrl+R toggles Run/Stop; F6 / Ctrl+Tab cycles Code -> Output -> Command.
# F11 / Alt+Enter maximizes/restores the active window; Ctrl+F4 closes it.
# Ctrl+S saves, Ctrl+O opens, Ctrl+F searches, Ctrl+X cuts, Ctrl+Q quits.
# Alt+F/E/S/R/D/O/I/H opens the corresponding menu.
# The Window menu reopens default windows; Ctrl+F6 compiles to Python.
exec sumx "${1:-examples/hello.prg}"
