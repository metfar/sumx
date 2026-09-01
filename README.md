# sumX 0.2.1

**0.2.1 architecture note:** positional source editing now delegates to the independent `sumIDE` xBase profile. The interpreter, SQLite/database runtime, console, `--run`, `--check`, and readable `--compile` path remain in sumX.

sumX is an xBase-inspired interpreter built on Python, SQLite and sumTUI. The current line is interpreter-first: a dBASE/FoxPro-style command window, modern runtime values, work-area/channel semantics, and direct access to the real SQLite engine underneath.

## Install

Install sumTUI first, then sumX:

```bash
pip install ./sumtui-0.7.0.tar.gz
pip install ./sumide-0.2.1.tar.gz
pip install ./sumdiff-0.2.1.tar.gz
pip install ./sumx-0.2.1.tar.gz
```

Run the sumTUI command window:

```bash
sumx
```

The command line deliberately distinguishes editing, running, checking, and generating readable Python:

```bash
sumx program.prg                         # open in the editor/IDE
sumx --run program.prg                   # full interactive runtime, no IDE/assistant
sumx --check program.prg                 # structural check only
sumx --compile program.prg               # generate program.py
sumx --compile program.prg -o output.py  # choose the generated file
sumx --compile program.prg -o -          # generated Python on stdout
sumx --plain                             # plain command REPL
sumx --plain --run program.prg           # textual program I/O, no TUI dialogs/forms
sumx --list-themes                        # available sumTUI themes
sumx --theme "Ralesk's MC" program.prg  # one-session theme override
sumx --line-continuation semicolon --run old.prg  # old xBase continuation
sumx --ampersand-comment --run old.prg            # && comments from first line
sumx -c 'A=SQL.SELECT count(*) FROM customers;'
```

Generated `.py` files receive executable permission on Unix and intentionally depend on the installed sumX runtime. There is no standalone/native compilation target.


When the optional `sumdiff` companion is installed, the source IDE exposes **File -> Compare with...**. It passes the current `.prg` editor buffer directly to sumdiff, including unsaved edits; if the source is saved while comparing, sumX reloads that saved version when the comparison closes.


## Running applications without the development assistant

`--run` means **run the program**, not **downgrade it to plain text**.  When stdin/stdout are attached to a terminal, sumX starts the normal interactive sumTUI runtime but does not display the command assistant or source IDE:

```bash
sumx --run examples/database.prg
```

The program may still use all interactive runtime services, including:

```text
DEFINE/ACTIVATE WINDOW
@ ... GET + READ
INPUT ... DIALOG
BROWSE
APPEND
DO FORM
```

For example, `BROWSE` opens the table browser and an argument-less `APPEND` opens the record-entry form.  Closing a modal resumes the `.prg` at the following statement.  When the program finishes, the temporary application screen closes and ordinary textual/history output is copied back to the invoking terminal.

The development environment is a separate concern.  A positional source file still opens the IDE/editor:

```bash
sumx examples/database.prg
```

The classic xBase name `ASSIST` is reserved for explicitly invoking the development assistant; `--run` never invokes it implicitly.

For scripts, redirected I/O, CI, or deliberately non-visual execution, use:

```bash
sumx --plain --run examples/database.prg
```

If no usable terminal is attached, `--run` falls back to this textual backend automatically.

## Project purpose

sumX tries to be an educational language environment.

Its main goals are readability, inspectability, portability,
experimentation and learning.

Even generated code is intended to remain understandable.

sumX does not aim to produce opaque standalone binaries.

The help system follows the same rule: every documented sumX language feature must carry at least one functional example. Examples are intended to be opened, changed, and run rather than treated as decorative snippets.

## Source editor and navigable help

Passing a source file positionally opens the common sumIDE xBase profile:

```bash
sumx examples/hello.prg
```

The editor is the shared `sumIDE 0.2.1` shell, with xBase execution supplied by sumX. Its top-level menus are:

```text
File  Edit  Search  View  Options  Window  Run  Help
```

**F9** opens/closes the menu and **F10** exits. **F2** opens Program Map, **F5/Ctrl+R** toggles cooperative Run/Stop, **F6/Ctrl+Tab** cycles Code → Output → Command, **F11/Alt+Enter** maximizes/restores, and **Ctrl+F6** compiles the current xBase buffer to readable Python. **Alt+I** opens Window; **Alt+W** is reserved for forward word/whitespace deletion. Selected-line `Tab`/`Shift+Tab`, whole-document tabs/spaces conversion, Vim modelines and the rest of the editing behavior come from the common sumTUI editor engine.

The xBase backend remains stateful: direct commands in the Command window keep the same interpreter/database session, and F5 execution advances cooperatively so the TUI can continue servicing keyboard and modal xBase operations. Program output is routed to Output rather than mixed into direct-command history.

### Preferences and runtime configuration

Source-editor preferences are centralized in **sumIDE**. Use **Options → Preferences...** for indentation, whitespace/control-character display, modelines, templates, files, keybindings, terminal settings and language defaults. The source IDE persists those settings in:

```text
~/.config/sumide/config.json
```

or `$XDG_CONFIG_HOME/sumide/config.json`. The file is an implementation detail; normal configuration is through the Preferences dialog.

The **sumX runtime/command environment** deliberately keeps its own runtime configuration under `~/.config/sumx/config.json` (or `$XDG_CONFIG_HOME/sumx/config.json`). That configuration controls runtime themes and xBase-environment behavior used by bare `sumx` and `sumx --run`; it no longer owns generic editor preferences. `--config FILE` selects an alternate runtime configuration.

A command-line theme can still override a session:

```bash
sumx --theme "Ralesk's MC" program.prg
sumx --theme DOS --run program.prg
sumx --list-themes
```

Interactive `HELP` remains provided by the sumX runtime/help corpus. A language feature is not considered documented until it has a functional example.

## Program output and diagnostics

Normal execution is quiet unless a statement explicitly requests screen output. Assignments, CREATE/USE/CHANNEL/APPEND/GO/SKIP and similar operational commands do not print by default:

```xbase
A = 5;
USE customers AS cust;
APPEND name="Ana";

? A;              # prints 5
BROWSE;            # displays the table
DISPLAY STRUCTURE; # displays structure
```

Operational messages can be enabled at runtime:

```xbase
SET DEBUG_LEVEL INFO;
A = 5;             # diagnostic: A = 5
USE customers;     # diagnostic: selected/opened channel information
SET DEBUG_LEVEL OFF;
```

Accepted levels are `OFF` (default), `INFO`, `DEBUG`, and `TRACE`. `DEBUG` and `TRACE` reserve room for deeper parser/runtime diagnostics as the interpreter grows; current command chatter is `INFO`. The historic-style `SET TALK ON/OFF` is an alias for `INFO/OFF`.

The CLI also accepts:

```bash
sumx --debug-level info --run examples/database.prg
```

Program output goes to stdout. Enabled informational/debug messages go to stderr, so shell redirection remains useful.

## Shell escape and command-window scrollback

At an interactive sumX prompt, a line beginning with `!` is sent to the host OS shell instead of the sumX parser:

```text
. !ls /
. !pwd
. !printf "hello\n"
```

The child command is non-interactive. Its combined stdout/stderr is copied into the sumX command window, so the result stays in the application's own output history. Use `PageUp` for older output and `PageDown` to move back toward the live prompt. Shift+Page remains an alias only on terminals that forward those keys to the application.

## Case rules and boolean aliases

Commands and keywords are always case-insensitive:

```xbase
browse;
BROWSE;
Browse;
```

Variables are case-insensitive by default. `CAPS_SENSITIVE` changes only variable names:

```xbase
SET CAPS_SENSITIVE OFF;   # default
Name = "Ana";
? name;                   # Ana

SET CAPS_SENSITIVE ON;
A = 10;
a = 20;
? A;                      # 10
? a;                      # 20
```

Switching back to `OFF` is rejected if variables differing only by case would collide.

Boolean/null aliases:

```text
.T. = TRUE = ON
.F. = FALSE = OFF
.NULL. = NULL = NONE = NIL
.AND. = AND
.OR. = OR
.NOT. = NOT
```

Assignments are aliases too:

```xbase
STORE 5 TO A;
LET A = 5;
A = 5;
```

## Coordinate screen output

Classic xBase `@ row,column SAY expression` is supported in the sumTUI command window. Coordinates are zero-based within the black command workspace:

```xbase
@ 5,5 SAY "La casa es roja";
@ 7,10 SAY 2+3;
```

The output is placed at the requested screen position and does not become ordinary scrolling diagnostic output. `@ ... GET` and `READ` are also available for editable classic screen fields.

## PRINT, PICTURE and TRANSFORM

`PRINT` is a sumX educational alias for the classic output forms `SAY`/`?`:

```xbase
PRINT "Hello";
? "Hello";
@ 5,10 PRINT "Hello";
```

Output formatting and `TRANSFORM()` share one PICTURE engine:

```xbase
nValue = 1250.50;
? nValue PICTURE "$999,999.99";
cFormatted = TRANSFORM(nValue, "$999,999.99");
PRINT cFormatted;
? TRANSFORM("usuario12", "@! NNNNNNNN");
```

Supported editable picture positions include `A`, `N`, `X`, `!`, `9`, `#`, `Y` and `L`; the engine recognizes `@!`, `@Z`, `@C`, `@X`, `@(`, `@E`, `@B`, `@R`, `@K`, `@G` (`YYYY.MM.DD`) and `@T` (`HH:mm:ss`).

PICTURE overflow is explicit:

```xbase
SET FIELD_WRAP_OVERFLOW OFF;  # default
? TRANSFORM("usuario12", "NNNNNNNN");  # usuario1

SET FIELD_WRAP_OVERFLOW ON;
? TRANSFORM("usuario12", "NNNNNNNN");  # usuario12
```

The same setting is used by direct `PICTURE` output and by `TRANSFORM()`. Numeric masks also report/retain overflow according to this setting rather than silently using a separate formatter.

## GET viewport: WIDTH and HEIGHT

`WIDTH` and `HEIGHT` describe the **visible viewport**, not the logical value length:

```xbase
@ 1,1 GET cred WIDTH 3 PICTURE "999XXX990";
@ 4,1 GET notes WIDTH 40 HEIGHT 6;
READ;
```

`HEIGHT` defaults to `1`. A one-line GET scrolls horizontally when the logical value is wider than its viewport. `HEIGHT > 1` enables multiline textarea-style editing with soft visual wrapping and vertical scrolling. Enter creates a real newline; Tab advances to the next GET and Tab on the final GET accepts READ. Ctrl+Enter remains an optional accept alias on terminals that can report it distinctly. PICTURE length/overflow remains independent from WIDTH/HEIGHT.

## Resizable screen dimensions

Terminal dimensions are expressed in text cells, so sumX uses rows/columns rather than ambiguous pixel-like width/height names:

```xbase
? WCOLS();
? WROWS();
```

`WCOLS()` and `WROWS()` are the primary xBase/Fox-style names. `SCREENCOLS()` and `SCREENROWS()` are descriptive aliases. In sumTUI they report the currently visible command workspace and therefore change after a terminal resize; in plain mode they fall back to the current terminal dimensions.

For example, a form can adapt without assuming an 80x25 screen:

```xbase
fieldWidth = WCOLS() - 4;
fieldHeight = WROWS() - 6;
@ 2,2 GET notes WIDTH fieldWidth HEIGHT fieldHeight;
READ;
```

## sumX statement syntax and source compatibility

The default, modern source mode is deliberately simple: a physical newline **or** a top-level `;` ends a statement, and a trailing backslash continues one logical command on the following physical line:

```xbase
A=1; B=2; ? A+B;

INPUT "Continue?" answer \
    KEYS "YN" \
    DEFAULT "N" \
    TIMEOUT 10 \
    DIALOG ;
```

So, in the default mode, this is **not** one INPUT command:

```xbase
INPUT "Continue?" answer ;
KEYS "YN" ;
DEFAULT "N" ;
```

For very old xBase sources, the physical-line continuation convention can be changed explicitly:

```xbase
SET LINE_CONTINUATION TO SEMICOLON

INPUT "Continue?" answer ;
    KEYS "YN" ;
    DEFAULT "N" ;
    TIMEOUT 10 ;
    DIALOG

SET LINE_CONTINUATION TO BACKSLASH
```

In `SEMICOLON` mode, a semicolon at the **end of a physical line** means continuation. An interior semicolon still separates statements, so `A=1; B=2` remains two commands. Old files that need the compatibility mode before their first statement can be opened/run/checked/compiled with `--line-continuation semicolon`.

`#` is the preferred and default comment marker:

```xbase
# full-line comment
USE customers AS cust;  # inline comment
```

By default `&&` is useful as a logical AND operator. Classic xBase `&&` inline comments are opt-in:

```xbase
SET AMPERSAND_COMMENT ON
A = 5 && classic xBase comment
? A
SET AMPERSAND_COMMENT OFF
```

The CLI equivalent for a source that starts with old-style `&&` comments is `--ampersand-comment`. Leading `*` comments remain accepted for classic source compatibility. Because `#` is a comment marker, inequality is `<>` or `!=`.

### Logical operator aliases

The keyword forms remain canonical and readable, while symbolic spellings are available when they make an example clearer:

```xbase
AND    &&
OR     ||
XOR    ^^
NOT    ~    ¬
```

For example:

```xbase
ready = ON
enabled = OFF

IF ready && ~enabled THEN PRINT "ready"
? ready || enabled
? ready ^^ enabled
```

When `SET AMPERSAND_COMMENT ON` is active, use `AND` instead of `&&`; the token has intentionally been reassigned to comment syntax in that compatibility mode.

Triple-quoted strings are supported:

```xbase
memo = """multiline
text; # this is data inside the string
""";
```

## Modern runtime values

sumX values map closely to useful Python concepts:

```text
INTEGER              int
NUMERIC/CURRENCY     Decimal semantics
FLOAT                float
LOGICAL              bool
CHAR/VARCHAR/MEMO    str
BLOB/BYTE            bytes
NULL                 None
LIST                 list
TUPLE                tuple
DICT                 dict
OBJ                  SumObject
ROW                  SumRow
CURSOR               SumCursor
QUERY                 SumQuery
```

Lists, dictionaries, indexing and slicing:

```xbase
A = [10,20,30,40];
? A[0];
? A[1:3];
A[1] = 99;
A.append(50);

D = {"Name":"Ana", "name":"Maria"};
? D["Name"];
```

`CAPS_SENSITIVE` does not alter dictionary keys or object members.

Dynamic objects:

```xbase
person = OBJ(
    name="Ana",
    active=ON,
    phones=["099111111", "29001111"]
);

? person.name;
person.name = "Bea";
person.phones.append("555-0100");
```

## Types for CREATE TABLE

- `AUTONUM` / `AUTOINCREMENT` / `IDENTITY` / `SERIAL`
- `INTEGER` / `INT` / `I`
- `NUMERIC(p,s)` / `DECIMAL(p,s)` / `NUMBER` / `N`
- `CURRENCY` / `MONEY` => fixed `NUMERIC(19,4)` semantics
- `FLOAT` / `REAL` / `DOUBLE` / `F`
- `CHARACTER(n)` / `CHAR(n)` / `C(n)`
- `VARCHAR(n)`
- `MEMO` / `M` => multiline text, logical maximum 65535 characters
- `TEXT`
- `LOGICAL` / `BOOL` / `BOOLEAN` / `L`
- `DATE`, `TIME`, `DATETIME` / `TIMESTAMP`
- `BLOB` / `BINARY` / `BYTE` / `BYTES`
- `UUID`, `JSON`

`MEMO` remains text; `BLOB/BYTE` is for arbitrary binary data. Fixed numeric values are stored as scaled integers so sumX can preserve fixed-decimal semantics.

## Channels / xBase work areas

There are 32 channels by default. Channel 1 is active at startup. `USE` always operates on the active channel; using another table there replaces the prior table/alias in that channel.

```xbase
USE customers AS cust;       # channel 1
CHANNEL 2;
USE sales AS sal;            # channel 2
CHANNEL cust;                # back to channel 1
BROW;
USE another;                 # replaces customers in channel 1
```

Canonical sumX spelling is `CHANNEL`; compatibility aliases are available:

```text
CHANNEL 2
CHAN 2
SELECT 2
SEL 2
SELE 2
```

Numeric/letter aliases are equivalent through Z:

```text
1 = A
2 = B
...
26 = Z
27..32 are numeric only
0 = next free channel
```

An open table alias can also select its channel (`CHANNEL cust`, `SEL cust`). The status bar shows both alias and table, for example:

```text
DB: shop.sqlite | [A/1:cust=customers] B/2:sal=sales | Rec 12/352
```

`BROW`, `BROWS`, and `BROWSE` are equivalent.

## Consumable real SQLite SQL

SQL is a first-class sumX value source, not only a print command.

Auto result conversion:

```text
1 row x 1 column        scalar
1 row x N columns       SumRow
0 or 2+ rows            SumCursor
INTO CURSOR name        SumCursor regardless of row count
non-query SQL           SqlExecResult
```

Inline:

```xbase
N = SQL.SELECT count(*) FROM customers;
rows = SQL.SELECT id,name FROM customers ORDER BY name;
```

Triple-quoted SQL:

```xbase
rows = SQL """
SELECT id, name
FROM customers
ORDER BY name;
""";
```

Block SQL:

```xbase
rows = SQL
SELECT customer_id, SUM(total) AS total
FROM sales
GROUP BY customer_id
INTO CURSOR totals
ENDSQL;
```

`INTO CURSOR` is handled by sumX and removed before the SQL reaches SQLite. In the example above, both `rows` and `totals` reference the same consumable cursor.

Explicit result modes:

```xbase
N = SQL.SCALAR SELECT count(*) FROM customers;
R = SQL.ROW SELECT id,name FROM customers WHERE id=1;
C = SQL.CURSOR SELECT id,name FROM customers;
SQL.EXEC UPDATE customers SET active=0 WHERE id=1;
```

Rows support positional, named and attribute access:

```xbase
R = SQL.ROW SELECT id,name FROM customers WHERE id=1;
? R[0];
? R["name"];
? R.name;
```

Reusable parameterized query objects are also available:

```xbase
Q = SQL.QUERY SELECT name FROM customers WHERE id=:id;
? Q.execute(id=2);
```

## Relationships and SQLite views

sumX keeps classic work-area relations and also supports persistent relationship metadata plus real SQLite views.

```text
LINK customers.id TO sales.customer_id AS customer_sales;
CREATE RELATION customer_sales FROM customers.id TO sales.customer_id;
DISPLAY RELATIONS;

CREATE VIEW customer_totals AS SQL.SELECT
    customer_id, SUM(total) AS total
    FROM sales
    GROUP BY customer_id;

CREATE VIEW customer_totals2 AS SQL
SELECT customer_id, SUM(total) AS total
FROM sales
GROUP BY customer_id
ENDSQL;

DISPLAY VIEWS;
USE customer_totals AS totals;
BROWSE;       # read-only because the source is a view
```

`LINK`/`CREATE RELATION` records a logical relationship for sumX tooling. Foreign keys declared with `REFERENCES` remain the SQLite-enforced integrity mechanism and are also shown by `DISPLAY RELATIONS`.

## Interactive help and record navigation

In the sumTUI command environment, `HELP` and F1 open a scrollable explorer dialog (`F11` maximizes/restores). The command window itself supports `PageUp` and `PageDown` for sumX output scrollback. `Shift+PageUp` / `Shift+PageDown` are aliases when the terminal forwards them; many Linux terminal emulators consume those shortcuts themselves.

Table-backed `BROWSE` is editable and shows `First | Prev | Next | Last | Search | New* | Edit | Exit`. `APPEND` and record edit dialogs show `First | Prev | Next | Last | Search | Ok | Cancel | Exit`; `Ctrl+End` saves and exits. SQL cursors and SQLite views remain read-only.

## Generic BROWSE

`BROWSE` still browses the active table, but now it can consume runtime values too:

```xbase
BROWSE customers_cursor;
BROW my_list_of_objects;
BROW my_dict;
```

This uses sumTUI `TableView`. With sumTUI 0.5.1, table/form dialogs can also be maximized/restored with F11.

## Current scope

The interpreter currently includes tables/types, channels/work areas, APPEND, BROWSE/LIST, forms generated from schemas, indexes/foreign keys, modern collection/object values, real SQLite SQL, `DO`/`RETURN`, one-line and block `IF`/`ELSE`/`ENDIF`, PICTURE/TRANSFORM formatting, viewport-aware GET fields, Fox/xBase-style named windows, a source editor, navigable example-driven help, and a first readable runtime-backed Python generator. `DO WHILE`, `FOR`, procedures, and debugger-level control flow remain later language stages.


## Optional THEN and IF blocks

`THEN` is optional for a block and useful for a one-line conditional. These three forms are valid:

```xbase
IF a == 5 THEN PRINT "listo";

IF a == 5
    PRINT "LISTO";
ENDIF

IF a == 5 THEN
    PRINT "LISTO";
    PRINT "ALGO MÁS";
ENDIF
```

`ELSE` is supported for block form. Parsing is based on logical lines after the configured continuation convention is applied.

The readable Python backend keeps the structure visible rather than flattening it into opaque runtime jumps. For example, the block above is emitted in the style of:

```python
if program.condition('a == 5', source_line=1):
    program.statement('PRINT "LISTO"', source_line=2);
```

See `examples/conditionals.prg` and `examples/python/conditionals_equivalent.py`.

## Fox/xBase-style named windows

A named window is defined by terminal-cell coordinates and is backed by the generic positioned `Dialog`/window primitive in sumTUI:

```xbase
DEFINE WINDOW wDialogo \
    FROM 8, 15 TO 16, 65 \
    TITLE " Confirmación " \
    SHADOW \
    PANEL \
    COLOR SCHEME 5

ACTIVATE WINDOW wDialogo
@ 1, 2 PRINT "¿Desea continuar?"
@ 3, 2 GET answer WIDTH 1 PICTURE "@! A"
READ
DEACTIVATE WINDOW wDialogo
RELEASE WINDOW wDialogo
```

While the window is active, `@ row,column` coordinates are relative to its interior. `SHOW WINDOW`/`HIDE WINDOW` are accepted as aliases for activate/deactivate. This is intentionally implemented through sumTUI rather than as a second windowing system inside the language. In the full-screen sumTUI environment the named window is rendered as a real positioned window; plain/compiled execution deliberately degrades the same program to ordinary textual input/output. See `examples/window.prg`.

## Classic GET / READ screen input

```xbase
nom=SPACE(30);
ape=REPLICATE(" ",30);
@5,1 SAY "Nombre:" GET NOM;
@7,1 SAY "Apellido:" GET APE;
READ;
```

`@ ... GET` fields are drawn at absolute coordinates in the sumTUI command workspace. A string initialized with `SPACE(n)` or `REPLICATE(" ",n)` becomes a fixed-width field of exactly `n` characters. `READ` activates all pending GETs. In one-line fields Enter advances and accepts on the last field; in multiline fields Enter inserts a newline. Tab advances in both modes and accepts on the final GET, Shift+Tab moves backward, Insert toggles insert/overwrite, and Esc cancels. When READ completes, the coordinate form is archived as ordinary command history before program execution continues, so finished GETs no longer remain live/highlighted in the output pane.

## BROWSE and APPEND are forms

In the full-screen sumTUI console, `BROWSE` and interactive `APPEND` are data forms rather than printed command results. This also applies when a `.prg` file is opened with `sumx program.prg` and run from the integrated editor.

```xbase
USE customers AS cust;
BROWSE;
APPEND;
```

`BROWSE` opens a table form whose column headings are the database field names. The selected row tracks the active work-area record. `APPEND` opens one record at a time, with generated fields such as:

```text
name:    [XXXXXXXXXXXXXXXXXXXX]
amount:  [9990.00]
active:  [x]
id:      [<auto>  ]
```

The field pictures are derived from sumX column metadata; SQLite remains the storage engine underneath. `sumx --plain` retains a textual fallback for non-TUI environments.

### Interactive APPEND

`APPEND` with no field list opens the simple schema-derived record editor.  All non-autonumeric fields are editable.  Use `Enter`/`Down`/`Tab` to move forward, `Up`/`Shift+Tab` to move backward, `Ctrl+End` to save, `Esc` to abort, and `F11` to maximize or restore the dialog.

### ACCEPT and console INPUT

Classic xBase `ACCEPT` is available for character input:

```xbase
ACCEPT "Por favor, ingresa tu nombre: " TO cNombre;
PRINT "Hola " + cNombre;
```

`ACCEPT` always stores the response as character text. sumX also includes a BASIC-like educational `INPUT` statement:

```xbase
INPUT "What is your name? " name;
PRINT "Hello " + name;
```

The comma and `TO` spellings of `INPUT` are also accepted. A new INPUT target receives character text; when the target already exists as a logical or numeric value, sumX attempts a type-compatible conversion.

INPUT can reuse the same presentation ideas as GET and the standalone `suminput` tool:

```xbase
INPUT "Password: " password HIDDEN;
INPUT "Password: " password MASK "***" WIDTH 20;
INPUT "Phone: " phone WIDTH 14 PICTURE "(999) 999-9999";
INPUT "Notes" notes WIDTH 50 HEIGHT 6 DIALOG;

INPUT "Continue? " answer \
    KEYS "YN" \
    DEFAULT "N" \
    TIMEOUT 10 \
    CASE_SENSITIVE \
    DIALOG ;
```

`HIDDEN` emits no entered characters; `MASK` emits only the mask string once per real character.  Secret values are not copied into sumX command history.  `KEYS` is the language-level equivalent of classic DOS `CHOICE`; `DEFAULT` and `TIMEOUT` make unattended scripts possible.  `WIDTH` and `HEIGHT` are presentation dimensions, while `PICTURE` remains a logical input/format mask.  Multiline INPUT currently does not combine with HIDDEN, MASK, KEYS, or PICTURE.

The companion shell command keeps stdout reserved for the result, so Bash can use:

```bash
name=$(suminput "Name: ")
pass=$(suminput --dialog --mask "*" "Password: ")
answer=$(suminput -c:YN -t:N,10 "Continue?")
```

This follows the broader project approach: where a small capability is already part of sumTUI/sumX and is reasonable to maintain, it can be exposed directly instead of forcing an unrelated external utility as a mandatory dependency.

## Runnable examples: sumX, Python and Bash

Where a feature crosses language/tool boundaries, the source tree includes examples in the corresponding environment:

```text
examples/conditionals.prg
examples/logical_aliases.prg
examples/legacy_continuation.prg
examples/window.prg
examples/python/conditionals_equivalent.py
examples/python/generated_conditionals.py
examples/bash/run_legacy.sh
examples/bash/compile_and_run.sh
examples/bash/open_editor.sh
examples/bash/run_interactive.sh
examples/bash/theme_config.sh
examples/python/run_interactive.py
examples/python/config_theme.py
examples/interactive_runtime.prg
```

Typical runs:

```bash
sumx --run examples/conditionals.prg
python3 examples/python/conditionals_equivalent.py
python3 examples/python/generated_conditionals.py
bash examples/bash/compile_and_run.sh
examples/bash/open_editor.sh
bash examples/bash/run_interactive.sh
bash examples/bash/theme_config.sh
python3 examples/python/run_interactive.py
python3 examples/python/config_theme.py
sumx --run examples/interactive_runtime.prg
```

The Python example is intentionally readable side-by-side material; `sumx --compile` remains the authoritative generated form. The Bash examples show how source compatibility and generated Python fit into ordinary shell workflows.

## BROWSE New* and compile-time themes

A table-backed `BROWSE` now exposes `First | Prev | Next | Last | Search | New* | Edit | Exit`. `New*` opens the same schema-derived append form used by interactive `APPEND`; after saving/closing, BROWSE refreshes and positions the work area on the appended record. Read-only cursors/views do not enable New*.

Compilation freezes presentation deliberately. `sumx --compile` uses the **effective theme at compile time** (or the explicit `--theme` override) and generated Python does not read the executing user's saved sumX theme to decide its appearance.

```bash
sumx --theme DOS --compile examples/window.prg -o /tmp/window.py
./tmp/window.py
```

For a built-in theme, generated Python stores the built-in theme name. For a user theme created with `sumtheme`, sumX embeds the complete effective theme dictionary directly in the generated Python, so that custom palette does not need to exist in `~/.config/sumtui/themes` on the machine/account where the generated program runs. The generated source keeps the settings visible as `PROGRAM_THEME_NAME` / `PROGRAM_THEME_DATA` for inspection.

Python example: `examples/python/theme_embedding.py`. Bash example: `examples/bash/compile_theme.sh`.


### Persistent IDE window layout

The Code, Output and Command workspace remembers each window position, size and maximized state when the IDE closes. Use **Window -> Reset Window Layout** to restore the built-in defaults and clear the saved geometry. Window layout is stored separately from the manually saved editor/theme options.


## Default interactive workspace

Running `sumx` with no arguments opens the common `sumIDE --language=xbase` workspace.  The **Command** window is visible and initially focused, while source programs can be created, opened, saved, saved as, and closed from **File**.  `sumx --console` retains the compact historical command-only frontend.

In the interactive help explorer, **F6** or **Ctrl+C** copies the current functional example to the clipboard; **F5** runs it.

<p align=center><b>- oOo -<b></p>
