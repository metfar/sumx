# Optional THEN and symbolic logical aliases.
a = 5
ready = ON
enabled = OFF

IF a == 5 THEN PRINT "single line IF"

IF ready && ~enabled THEN
    PRINT "block line 1"
    PRINT "block line 2"
ELSE
    PRINT "not ready"
ENDIF

PRINT "XOR:";
? ready ^^ enabled;
