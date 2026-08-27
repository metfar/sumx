# DOS CHOICE-style one-key input.
INPUT "Continue? " answer KEYS "YN" DEFAULT "N" TIMEOUT 10 DIALOG;
PRINT "Answer: " + answer;
