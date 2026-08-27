# WIDTH/HEIGHT are presentation dimensions, not data length.
cred = "ABC123450";
notes = "A multiline GET can be narrower and shorter than its logical value.";
@ 1,1 PRINT "Credential:" GET cred WIDTH 3 PICTURE "XXX 999 990";
@ 3,1 PRINT "Notes:";
@ 4,1 GET notes WIDTH 30 HEIGHT 4;
READ;
PRINT cred;
PRINT notes;
