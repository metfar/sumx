# Secret input. The entered value is not echoed in clear text.
INPUT "Password: " password MASK "*" WIDTH 20 DIALOG;
PRINT "Password received.";
