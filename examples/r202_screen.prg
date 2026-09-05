# sumX r20.2.2: common aliases, dynamic grid and visible cursor states.
? TRUE
? true
? FALSE
? false
? NULL
? nil
? none
? "Screen: " + STR(COLS()) + "x" + STR(ROWS())

? "Cursor hidden for .75 s"
CURSOR OFF
PAUSE .75

? "Cursor normal/underscore for .75 s"
CURSOR ON
PAUSE .75

? "Cursor block for .75 s"
CURSOR BLOCK
PAUSE .75

? "Cursor restored to normal"
CURSOR ON
