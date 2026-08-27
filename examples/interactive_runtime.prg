# Interactive application runtime demo.
# Run with: sumx --run examples/interactive_runtime.prg

CREATE TABLE students (
    id AUTONUM,
    name VARCHAR(40),
    notes MEMO
)
USE students AS students

# Argument-less APPEND opens an interactive record form in --run mode.
APPEND

# BROWSE opens the interactive table browser and resumes here when closed.
BROWSE

PRINT "Interactive application finished."
