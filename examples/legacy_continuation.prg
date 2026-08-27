# Old xBase-style physical line continuation.
SET LINE_CONTINUATION TO SEMICOLON

INPUT "Continue? " answer ;
    KEYS "YN" ;
    DEFAULT "N" ;
    DIALOG

PRINT "Answer: " + answer

# Return to the modern default for any following source.
SET LINE_CONTINUATION TO BACKSLASH
