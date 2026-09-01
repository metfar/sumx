# sumX Help

Every documented language feature includes a functional example.

## Programming

### DO

Executes another sumX program file (.PRG).

#### Syntax

```text
DO program
DO path/to/program.prg
```

#### Notes

- The .prg extension is optional.
- Relative paths are resolved from the calling program first.

#### Functional example

```xbase
PRINT "Before"
DO examples/hello
PRINT "After"
```

#### See also

RETURN, --run

### RETURN

Stops the current program file and returns to its caller.

#### Syntax

```text
RETURN
```

#### Functional example

```xbase
PRINT "This is printed"
RETURN
PRINT "This is not printed"
```

#### See also

DO

### FUNCTION

Defines a reusable xBase function or procedure. Functions may be called from expressions, including a GET `VALID` clause.

#### Syntax

```text
FUNCTION name
    PARAMETER parameter [, parameter ...]
    statements
    RETURN expression
[ENDFUNC]

FUNCTION name(parameter [, parameter ...])
    statements
    RETURN expression
[ENDFUNC]
```

#### Notes

- `PARAMETER` and `PARAMETERS` are accepted.
- `RETURN expression` returns a value to the calling expression; bare `RETURN` returns without a value.
- A function placed at the end of a program may end at EOF, matching the classic xBase source-file style; explicit `ENDFUNC` / `ENDPROCEDURE` is also accepted.
- Interactive requests such as READ are not allowed while a function is being evaluated as an expression.

#### Functional example

```xbase
FUNCTION ValidarRespuesta
    PARAMETER cValor
    IF NOT (cValor $ "SN")
        RETURN FALSE
    ENDIF
    RETURN TRUE
```

#### See also

RETURN, GET, MESSAGEBOX

### IF

Conditionally executes one statement or a block; THEN is optional for block form.

#### Syntax

```text
IF condition THEN statement
IF condition
    statements
ENDIF
IF condition THEN
    statements
[ELSE
    statements]
ENDIF
```

#### Notes

- A one-line IF with code after THEN does not require ENDIF.
- IF ... THEN with THEN at the end of the logical line starts a block.

#### Functional example

```xbase
a = 5
IF a == 5 THEN PRINT "single line"
IF a == 5 THEN
    PRINT "block line 1"
    PRINT "block line 2"
ENDIF
```

#### See also

LOGICAL OPERATORS

### LOGICAL OPERATORS

Boolean operators have keyword and symbolic spellings.

#### Syntax

```text
AND / &&
OR / ||
XOR / ^^
NOT / ~ / ¬
```

#### Notes

- # is the default comment introducer.
- SET AMPERSAND_COMMENT ON reassigns && to classic xBase inline-comment syntax; AND remains available.

#### Functional example

```xbase
ready = ON
enabled = OFF
? ready && ~enabled
? ready || enabled
? ready ^^ enabled
```

#### See also

IF, SET AMPERSAND_COMMENT

## Settings

### SET AMPERSAND_COMMENT

Chooses whether && means logical AND or a classic xBase inline comment.

#### Syntax

```text
SET AMPERSAND_COMMENT OFF
SET AMPERSAND_COMMENT ON
```

#### Notes

- OFF is the default, so && is normally AND.
- # remains the preferred/default comment marker in both modes.

#### Functional example

```xbase
SET AMPERSAND_COMMENT OFF
? ON && ON
SET AMPERSAND_COMMENT ON
A = 5 && this text is now a comment
? A
```

#### See also

LOGICAL OPERATORS

#### Aliases

AMPERSAND_COMMENT

### SET LINE_CONTINUATION

Selects the physical-line continuation convention used by the source reader.

#### Syntax

```text
SET LINE_CONTINUATION TO BACKSLASH
SET LINE_CONTINUATION TO SEMICOLON
```

#### Notes

- BACKSLASH is the modern/default mode: newline or ; ends a statement and trailing \ continues it.
- SEMICOLON compatibility mode treats a semicolon at the end of a physical line as continuation; interior semicolons still separate statements.

#### Functional example

```xbase
SET LINE_CONTINUATION TO SEMICOLON
INPUT "Continue?" answer ;
    KEYS "YN" ;
    DEFAULT "N" ;
    DIALOG
SET LINE_CONTINUATION TO BACKSLASH
```

#### See also

INPUT

#### Aliases

LINE_CONTINUATION

## Screen I/O

### DEFINE WINDOW

Defines a Fox/xBase-style named window backed by a sumTUI dialog/window primitive.

#### Syntax

```text
DEFINE WINDOW name FROM row,col TO row,col [TITLE text] [SHADOW] [PANEL] [COLOR SCHEME n]
ACTIVATE WINDOW name
DEACTIVATE WINDOW [name]
RELEASE WINDOW name
```

#### Notes

- @ row,column coordinates are relative to the active window while it is active.
- The positioned screen inherits the window COLOR SCHEME; blank cells around PRINT text no longer fall back to the global Command background.
- A READ inside the window keeps keyboard focus in that window until the GETs are accepted or cancelled.
- SHOW/HIDE WINDOW are accepted as ACTIVATE/DEACTIVATE aliases.

#### Functional example

```xbase
answer = "N"
DEFINE WINDOW wDialogo FROM 4,10 TO 12,55 TITLE " Confirmación " SHADOW PANEL COLOR SCHEME 5
ACTIVATE WINDOW wDialogo
@ 1,2 PRINT "¿Continuar?"
@ 3,2 GET answer WIDTH 1 PICTURE "@! A"
READ
DEACTIVATE WINDOW wDialogo
RELEASE WINDOW wDialogo
PRINT answer
```

#### See also

GET, READ

#### Aliases

WINDOW

## Database

### APPEND

Adds a record to the active table; without values it opens the interactive record form when a TUI runtime is available.

#### Syntax

```text
APPEND
APPEND BLANK
APPEND field=expression [, field=expression ...]
```

#### Notes

- sumx --run program.prg keeps this interactive form available without opening the IDE.
- sumx --plain --run program.prg uses textual prompts instead.

#### Functional example

```xbase
CREATE TABLE demo (id AUTONUM, name VARCHAR(30))
USE demo
APPEND
BROWSE
```

#### See also

BROWSE

### BROWSE

Opens an interactive table browser for the active table or displays a browsable expression/cursor.

#### Syntax

```text
BROWSE
BROW
BROWSE expression [LIMIT n]
```

#### Notes

- In interactive --run mode the browser is a sumTUI modal and program execution resumes after it closes.
- Table-backed BROWSE includes New* to append a record directly and then refresh the browser.
- Views and expression/cursor results may be read-only.

#### Functional example

```xbase
CREATE TABLE demo (id AUTONUM, name VARCHAR(30))
USE demo
APPEND name="Ana"
APPEND name="Luis"
BROWSE
```

#### See also

APPEND

## Screen I/O

### PRINT

sumX alias for SAY/output, provided as a familiar educational spelling.

#### Syntax

```text
PRINT expression [PICTURE picture]
@ row,column PRINT expression [PICTURE picture]
@ row,column PRINT expression GET variable [...]
```

#### Notes

- Classic ? and SAY forms remain available.

#### Functional example

```xbase
name = "Ana"
PRINT "Hello " + name
PRINT 1250.50 PICTURE "$999,999.99"
```

#### See also

SAY, PICTURE, TRANSFORM

## Formatting

### PICTURE

Formats output and defines GET input/display masks.

#### Syntax

```text
? expression PICTURE picture
PRINT expression PICTURE picture
@ row,column SAY expression PICTURE picture
GET variable PICTURE picture
```

#### Notes

- A/N/X/!/9/#/Y/L are editable mask positions.
- @!, @Z, @C, @X, @(, @E, @B, @R, @K, @G and @T are supported modifiers.
- `@M value1,value2,...` defines an allowed-choice mask. For example, `PICTURE "@M S,N"` accepts only S or N and canonicalizes matching lowercase keystrokes to the listed value.
- A pure transform such as `PICTURE "@!"` uppercases input without imposing a zero-length logical mask.

#### Functional example

```xbase
nValue = 1250.50
? nValue PICTURE "$999,999.99"
? "usuario12" PICTURE "@! NNNNNNNN"
answer = "N"
@ 1,1 GET answer PICTURE "@M S,N"
```

#### See also

TRANSFORM, SET FIELD_WRAP_OVERFLOW, GET

### TRANSFORM

Returns the formatted representation of a value using the same PICTURE engine as output and GET.

#### Syntax

```text
TRANSFORM(value, picture)
```

#### Functional example

```xbase
cFormatted = TRANSFORM(1250.50, "$999,999.99")
PRINT cFormatted
? TRANSFORM("usuario12", "@! NNNNNNNN")
```

#### See also

PICTURE, SET FIELD_WRAP_OVERFLOW

## Settings

### SET FIELD_WRAP_OVERFLOW

Controls whether values may continue beyond the logical PICTURE mask.

#### Syntax

```text
SET FIELD_WRAP_OVERFLOW OFF
SET FIELD_WRAP_OVERFLOW ON
```

#### Notes

- OFF is the default.
- WIDTH and HEIGHT are display viewport dimensions and are independent of this setting.

#### Functional example

```xbase
SET FIELD_WRAP_OVERFLOW OFF
? TRANSFORM("usuario12", "NNNNNNNN")
SET FIELD_WRAP_OVERFLOW ON
? TRANSFORM("usuario12", "NNNNNNNN")
```

#### See also

PICTURE, GET

#### Aliases

FIELD_WRAP_OVERFLOW, SET FIELD WRAP OVERFLOW

### SET CONFIRM

Controls what happens when editing reaches the logical end of a bounded input field.

#### Syntax

```text
SET CONFIRM ON
SET CONFIRM OFF
```

#### Notes

- ON is the sumX default: the field remains active until Enter, Tab or another navigation key confirms it.
- While ON, typing beyond the logical end overwrites the final logical character repeatedly. A one-character field receiving `Y`, then `E`, then `S` therefore contains `S`.
- OFF automatically advances to the next GET as soon as the logical limit is filled; on the last GET it accepts the READ.
- The logical limit is independent of the visible WIDTH. A scrolling field may have a larger logical capacity than its viewport.
- This setting mirrors the classic xBase/Fox `SET CONFIRM` concept while choosing ON as the safer modern default in sumX.

#### Functional example

```xbase
answer = "N"
SET CONFIRM ON
@ 1,1 GET answer WIDTH 1 PICTURE "@! A"
READ
? answer
```

#### See also

GET, READ, PICTURE

## Screen I/O

### GET

Defines an editable field at an absolute screen coordinate.

#### Syntax

```text
@ row,column GET variable [WIDTH n] [HEIGHT n] [PICTURE picture] [VALID expression] [ERROR expression]
@ row,column SAY expression GET variable [WIDTH n] [HEIGHT n] [PICTURE picture] [VALID expression] [ERROR expression]
```

#### Notes

- WIDTH is visible columns only.
- HEIGHT defaults to 1; HEIGHT > 1 is a multiline textarea-like field.
- READ starts in classic overwrite mode; typing into a full bounded field replaces the character under the caret instead of rejecting the keystroke.
- With SET CONFIRM ON, further typing at the logical end repeatedly overwrites the final logical character; with SET CONFIRM OFF, filling the logical field advances automatically.
- PICTURE validation is applied while typing, including transformations such as `@!` uppercase and choice masks such as `@M S,N`.
- `VALID expression` is evaluated against the candidate value before READ can leave the field. The candidate is temporarily visible through the GET variable, so `VALID answer $ "SN"` works directly.
- `ERROR expression` supplies the message shown when VALID returns false. Without ERROR, a validation function may display its own MESSAGEBOX and return false to keep focus on the GET.
- Tab moves to the next GET only after validation succeeds; Tab on a valid last GET accepts READ.

#### Functional example

```xbase
answer = "N"
@ 2,2 SAY "Continue?"
@ 3,2 GET answer PICTURE "@!" VALID answer $ "SN" ERROR "Use S or N"
READ
PRINT answer
```

#### See also

READ, PICTURE, FUNCTION, MESSAGEBOX

### READ

Activates pending GET fields and writes accepted values back to their variables.

#### Syntax

```text
READ
```

#### Notes

- In sumIDE, a screen READ automatically activates the Command workspace so its GET fields receive keyboard input.
- A READ inside DEFINE WINDOW remains focused in that modal window.
- Enter accepts the last one-line GET; Tab advances and accepts on the last field; Esc cancels.
- SET CONFIRM ON keeps a bounded GET active at its logical end; SET CONFIRM OFF auto-advances when that logical limit is filled.

#### Functional example

```xbase
name = SPACE(20)
@ 2,2 SAY "Name:" GET name WIDTH 12
READ
PRINT name
```

#### See also

GET

## Console I/O

### ACCEPT

Reads a character response using the classic xBase ACCEPT ... TO syntax.

#### Syntax

```text
ACCEPT "Prompt" TO variable
```

#### Notes

- ACCEPT always stores character text, even when the target variable previously contained another type.

#### Functional example

```xbase
ACCEPT "Por favor, ingresa tu nombre: " TO cNombre;
PRINT cNombre;
```

#### See also

INPUT, PRINT

### INPUT

Reads a console response into a variable using a BASIC-like educational syntax.

#### Syntax

```text
INPUT "Prompt" variable
INPUT "Prompt" variable WIDTH n [HEIGHT n]
INPUT "Prompt" variable PICTURE picture
INPUT "Prompt" variable HIDDEN
INPUT "Prompt" variable MASK "*"
INPUT "Prompt" variable KEYS "YN" [DEFAULT "N"] [TIMEOUT 10] [CASE_SENSITIVE] [DIALOG]
INPUT "Prompt" variable \  ... \  DIALOG ;
```

#### Notes

- If the target already exists, sumX converts the response to its current logical/numeric type when possible.
- A new target is created as character text.
- HIDDEN echoes nothing; MASK repeats only the supplied visual mask per entered character.
- WIDTH/HEIGHT are presentation dimensions; PICTURE remains an input/format mask.
- KEYS provides DOS CHOICE-style one-key input; DEFAULT and TIMEOUT support unattended input.
- By default, newline or a top-level semicolon ends the command; a trailing backslash continues the logical line. SET LINE_CONTINUATION TO SEMICOLON enables legacy semicolon-at-EOL continuation.
- Multiline INPUT currently does not combine with HIDDEN, MASK, KEYS or PICTURE.

#### Functional example

```xbase
INPUT "Continue?" answer \n    KEYS "YN" \n    DEFAULT "N" \n    TIMEOUT 10 \n    DIALOG ;
PRINT answer;
```

#### See also

ACCEPT, GET, READ, PRINT, PICTURE

## Environment

### WCOLS

Returns the number of visible columns in the current sumX command workspace.

#### Syntax

```text
WCOLS()
```

#### Notes

- In plain mode it falls back to the terminal width.
- SCREENCOLS() is a descriptive alias.

#### Functional example

```xbase
? WCOLS()
```

#### See also

WROWS

#### Aliases

SCREENCOLS

### WROWS

Returns the number of visible rows in the current sumX command workspace.

#### Syntax

```text
WROWS()
```

#### Notes

- In plain mode it falls back to the terminal height.
- SCREENROWS() is a descriptive alias.

#### Functional example

```xbase
? WROWS()
```

#### See also

WCOLS

#### Aliases

SCREENROWS

### MESSAGEBOX

Displays a modal message from an xBase expression. It is especially useful inside reusable GET validation functions.

#### Syntax

```text
MESSAGEBOX(text [, flags [, title]])
```

#### Notes

- `flags` accepts the traditional numeric Fox-style value. Icon/severity values use the active sumTUI palette: `16` stop/error (red), `32` question (blue), `48` exclamation/warning (yellow), and `64` information (cyan-like).
- In the interactive sumIDE/sumX TUI runtime the message is shown as a modal dialog. The current implementation returns `1` immediately; use it as an alert rather than depending on a button-result code.
- In readable compiled/plain execution, MESSAGEBOX has a textual diagnostic fallback.

#### Functional example

```xbase
FUNCTION ValidarRespuesta
    PARAMETER cValor
    IF NOT (cValor $ "SN")
        = MESSAGEBOX("¡Atención! Solo se permite 'S' o 'N'.", 48, " Error ")
        RETURN FALSE
    ENDIF
    RETURN TRUE

answer = "N"
@ 1,1 GET answer PICTURE "@!" VALID ValidarRespuesta(answer)
READ
```

#### See also

GET, FUNCTION, RETURN

### SHELL ESCAPE

Runs a non-interactive operating-system shell command and keeps its output in command history.

#### Syntax

```text
!command
```

#### Functional example

```xbase
!printf "hello from the shell\n"
```

#### See also

DO

#### Aliases

!
