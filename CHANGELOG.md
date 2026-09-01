# Changelog

## 0.2.8 - 2026-09-01

- Requires sumIDE 0.2.6 so the `sumx` IDE launcher uses the dedicated sumX syntax lexer rather than generic FoxPro highlighting.
- Fixes `#` comment highlighting in the IDE: the complete comment line is styled as a comment, without highlighting `THEN`, `AND`, or other tokens inside it.

## 0.2.7 - 2026-09-01

- Added classic GET validation clauses: `VALID expression` evaluates the candidate value before READ can leave the field, and `ERROR expression` supplies the validation message while focus remains on the GET. The xBase membership operator `$` is accepted in expressions, so `VALID answer $ "SN"` works directly.
- Added `PICTURE "@M S,N"` choice masks. The mask filters/canonicalizes allowed keystrokes and validates the complete value without confusing logical capacity with visible `WIDTH`. Pure transform masks such as `PICTURE "@!"` remain editable.
- Added callable user `FUNCTION`/`PROCEDURE` validation with `PARAMETER(S)` and value-returning `RETURN expression`, sufficient for reusable `VALID ValidarRespuesta(answer)` routines.
- Added `MESSAGEBOX(text [, flags [, title]])` to the xBase expression/runtime layer. In sumIDE/sumX console it opens the common modal dialog; generated/plain runtime has a textual fallback. This supports validation functions that display their own error and return `.F.`/`FALSE` to keep focus on the GET.
- MESSAGEBOX icon/severity flags now carry semantic colors through the common sumTUI palette: `16` stop/error is red, `32` question is blue, `48` exclamation/warning is yellow and `64` information is cyan-like, with automatic contrasting title/text colors.
- Kept validation integrated with `SET CONFIRM`: an invalid bounded field never auto-advances, even with CONFIRM OFF; it remains overwrite-editable until a valid value is entered.
- Updated readable-Python compilation to register user functions before main execution and to reprompt compiled READ fields until validation succeeds.
- Requires `sumTUI >= 0.7.7` and `sumIDE >= 0.2.5`. Regression suite: 115 tests passing.

## 0.2.6 - 2026-09-01

- Fixed bounded GET editing at the logical end: with confirmation enabled, a one-character field receiving `Y`, `E`, `S` now remains active and ends with `S`; subsequent keys overwrite the final logical character instead of being ignored.
- Added `SET CONFIRM ON/OFF`. ON is the sumX default and requires explicit Enter/Tab/navigation to leave a bounded GET; OFF auto-advances when the logical field limit is filled and accepts READ on the final GET.
- Routed PICTURE validation through the actual logical replacement cell at the end of a full field, so masks such as `PICTURE "@! A"` continue to accept and transform repeated replacement keystrokes.
- Applied the same confirmation policy to xBase INPUT/dialog text fields through the common sumTUI bounded-field implementation.
- Requires `sumTUI >= 0.7.5` and `sumIDE >= 0.2.5`.

## 0.2.5 - 2026-09-01

- Fixed GET/READ keyboard routing in the common sumIDE shell: when a running xBase program reaches a normal screen READ, the Command workspace is activated so the field actually receives keystrokes.
- Fixed classic overwrite semantics for bounded/Picture GETs: a one-character field initialized to `N` can be replaced directly by typing `Y`, `S`, etc., without deleting the default first. PICTURE validation still applies while typing.
- Fixed `DEFINE WINDOW` rendering so unoccupied cells and `@ ... PRINT` text inherit the selected `COLOR SCHEME` background instead of leaking the global Command-window background through the dialog.
- Verified the same READ behavior inside a named window: the modal window receives input, accepts Enter/Tab, resumes the program, deactivates/releases cleanly, and returns subsequent PRINT output to the IDE Output pane.
- Updated the common IDE integration for the visible Code/Output/Command startup layout and Output-on-F5 behavior.

## 0.2.4 - 2026-09-01

- Kept `help.md` as the canonical editable xBase reference while switching runtime loading to the generated `help.helpdb` cache.
- `.helpdb` generation is now owned by SumDoc 0.2.1; sumX only consumes the compiled help format through sumTUI's lightweight runtime model.
- Added `help.helpdb` to package data so installed help does not require SumDoc or Markdown parsing at runtime.
- Preserved the historical `sumx.helpdb` provider API used by sumIDE and `sumx --console`.

## 0.2.3 - 2026-09-01

- Moved the canonical xBase reference out of Python literals into the editable packaged `sumx/help.md`.
- `helpdb.py` became a compatibility adapter over the Markdown corpus.
- Classic `sumx --console` help gained scrollbars for topics/content and F2 Topic Map navigation.

## 0.2.2 - 2026-09-01

- Updated the common IDE integration to sumIDE 0.2.2 so F1 from an xBase buffer opens the existing sumX topic/help database instead of generic editor help.
- Kept the sumX help corpus owned by sumX and discoverable by sumIDE through the language profile.

## 0.2.1 - 2026-09-01

- `sumx` with no arguments now opens the common sumIDE xBase workspace with Command visible and initially focused.
- Added `sumx --console` for the historical command-only frontend.
- Source programs remain managed through sumIDE File operations, including the new Close action.
- sumX Help now supports F6 / Ctrl+C to copy the current functional example while F5 continues to run it.
- Requires `sumTUI >= 0.7.1` and `sumIDE >= 0.2.1`.

## 0.2.0 - 2026-09-01

- Started the post-split sumX release line: the xBase interpreter, SQLite/database runtime, command environment, `--run`, `--check` and readable Python `--compile` remain in sumX, while positional source editing delegates to the independent `sumIDE` xBase profile.
- Retained `sumx.editor_app.SumXEditorApp` as the stateful xBase language backend attached to the common IDE shell. Cooperative F5 Run/Stop, direct commands, database state and readable-Python compilation remain in sumX, while editing/windows/preferences/templates stay in sumIDE.
- Adopted the current `sumTUI 0.7.0` editor behavior and `sumIDE 0.2.0` preferences/templates/profile architecture. Positional source editing now uses sumIDE configuration; the separate sumX configuration remains for the command environment and program runtime.
- The modern source rules remain unchanged: newline or `;` terminates statements, backslash is the default physical-line continuation, legacy semicolon continuation is optional, `#` is the default comment introducer, and symbolic logical aliases remain available.
- Requires `sumTUI >= 0.7.0` and `sumIDE >= 0.2.0`.

## 0.1.16

- Moved the positional-file source editor to the independent `sumIDE` project. `sumx program.prg` now enters the common xBase IDE profile while `sumx --run`, `--compile`, `--check`, `-c/--command` and the console runtime remain owned by sumX.
- Replaced `sumx.editor_app.SumXEditorApp` with a compatibility wrapper around `sumide.app.ScriptIDE`, preserving the import/API path while eliminating the duplicate IDE implementation.
- Requires `sumTUI >= 0.6.2` and `sumIDE >= 0.1.0a1`.

## 0.1.15

- Adopted sumTUI 0.6.1 editor deletion and block-indentation behavior: Alt+W, Ctrl+Alt+W, Tab and Shift+Tab.
- Reassigned the Window menu to **Alt+I** and disabled automatic menu mnemonics so **Alt+W** cannot be stolen from the editor at line boundaries.
- Added configurable editor Tab width (2/4/8), persisted with the existing editor configuration.
- Added whole-buffer Tabs -> N spaces and N spaces -> Tabs conversions under Edit.
- Updated dependency to `sumtui>=0.6.1`. Regression suite remains 97 tests plus new menu-binding coverage.

## 0.1.14

- Integrated the source editor with optional `sumdiff` through **File -> Compare with...**.
- The live xBase buffer is handed to sumdiff without requiring a preliminary save; if sumdiff saves the source, the sumX editor reloads that file on return.
- Updated the dependency to `sumTUI >= 0.6.0`; `sumdiff` remains an optional separate application rather than a hard sumX dependency.
- Regression suite: 97 tests.

## 0.1.13

- sumX IDE now restores Code, Output and Command window geometry across runs through the common sumTUI workspace layout store.
- Added **Window -> Reset Window Layout** to restore default positions/sizes and clear persisted geometry.
- Updated the sumTUI dependency to 0.5.29 for workspace layout persistence.

## 0.1.12

- sumX source-editor windows now expose the shared sumTUI 0.5.28 geometry controls: drag the lower-right corner to resize, Alt+M for keyboard Move, and Alt+Z for keyboard Resize.
- In keyboard Move/Resize, arrows adjust one cell, Shift+arrows adjust five, Enter accepts, and Escape restores the original geometry.
- Added Move/Resize to the Window menu and editor-key help; requires `sumtui>=0.5.28`.

## 0.1.11

- F2 Program Map now opens with the entry containing the current editor cursor already selected, matching the shared QBasic-style navigation behavior in sumTUI 0.5.27.
- Updated the declared sumTUI dependency to `sumtui>=0.5.27`.
- Regression suite: 96 tests.

## 0.1.10

- F2 now opens the xBase Program Map (MAIN, PROCEDURE, FUNCTION, classes/methods) instead of saving. Ctrl+S remains Save.
- Standardized Ctrl+O Open, Ctrl+F Find, Ctrl+X Cut, Ctrl+Q Quit, F5/Ctrl+R Run/Stop, F6/Ctrl+Tab Next Window and F11/Alt+Enter Maximize/Restore.
- Added Termux-friendly Alt menu accelerators and Alt+P Program Map.
- Added SAVE_AND_EXIT / FORGET_AND_EXIT / CANCEL protection before destructive actions on modified source.
- Output and Command now use visible scroll panes, and program output preserves line boundaries.
- Requires sumTUI 0.5.22 or newer. Regression suite: 95 tests.

## 0.1.9

- Migrated the source IDE to sumTUI 0.5.20 `Workspace` windows. Code, Output, and the stateful xBase Command console are now separate movable/overlapping windows rather than a fixed editor plus combined output/command area.
- Added a dynamic **Window** menu to activate, close, and reopen the persistent default windows. F6 cycles Code → Output → Command, F11 maximizes/restores the active window, and Ctrl+F4 closes it; Ctrl+F6 remains Compile to Python.
- Program output is routed to the Output window while direct commands remain in their own persistent Command history.
- Updated editor documentation and Bash examples for the shared Sum IDE window convention.
- Requires sumTUI 0.5.20 or newer. Regression suite: 94 tests.

## 0.1.8

- Documentation/example consistency pass: README version/install examples now match 0.1.8, and `examples/bash/open_editor.sh` documents the current IDE convention (`F5` Run/Stop, `F6` Next Window, `Ctrl+F6` Compile).
- Updated the declared sumTUI dependency to `sumtui>=0.5.19`.
- No language/runtime behavior changed from 0.1.7; regression suite remains 92 tests.

## 0.1.7

- Unified IDE function keys with the rest of the Sum editors: **F5 = Run/Stop**, **F6 = switch Editor / Output-Command window**.
- IDE execution is cooperative in bounded statement batches, so the sumTUI event loop remains responsive and F5 can stop a running program instead of waiting for the whole buffer to finish.
- Moved Compile to Python from F6 to **Ctrl+F6**; the Run menu and function bar reflect the new assignments.
- SumX editor action rows no longer force one-row button containers, allowing the multi-row Button geometry provided by sumTUI 0.5.18 to propagate through editor dialogs.
- Updated dependency to `sumtui>=0.5.18`.
- Regression suite: 92 tests.

## 0.1.6

- `BROWSE` now includes a `New*` action beside Search/Edit so a table-backed browser can append a new record directly, return to the browser, refresh, and keep the work-area position on the new record.
- `sumx --compile` now freezes the effective theme at compile time instead of consulting the executing user's sumX theme configuration later.
- Built-in themes are stored compactly by built-in name in generated Python. User/custom themes are serialized as full effective theme data directly into the generated `.py`, so the compiled program does not need that custom theme installed on the target account.
- The compile-time `--theme NAME` override determines the frozen theme; when omitted, the saved/effective sumX theme at compile time is used.
- Generated input dialogs receive the frozen theme through the runtime helper.
- Added theme-embedding and BROWSE New* regression coverage plus Python/Bash examples for inspecting compile-time theme embedding.
- Requires sumTUI 0.5.11 or newer.

## 0.1.5

- Added persistent sumX application configuration at `~/.config/sumx/config.json`, respecting `$XDG_CONFIG_HOME`; `--config FILE` can select an alternate file.
- Added **Options > Theme** and **Options > Save configuration** to both the command environment and source editor.
- The source editor now restores saved whitespace/control-character visibility options together with the selected theme.
- `sumx --run` remains assistant-free but now automatically uses the saved theme for interactive windows, BROWSE, APPEND, GET/READ and dialogs.
- Added `--theme` as a per-session override and `--list-themes` to show the themes supplied by sumTUI.
- Added Python and Bash configuration/theme examples and updated built-in configuration help and README documentation.
- Requires sumTUI 0.5.10 or newer.

## 0.1.4

- `sumx --run file.prg` now uses the full interactive sumTUI application runtime whenever a terminal is available, without opening the command assistant or IDE.
- Interactive `--run` supports DEFINE WINDOW, GET/READ, INPUT DIALOG, BROWSE, APPEND and FORM modals and resumes program execution when each modal closes.
- `--plain --run` explicitly selects the textual backend; non-TTY execution falls back to it automatically.
- Program-only mode has no hidden File/Database/Help assistant menu or command prompt. F10/Ctrl+C abort the running application.
- Text/history output is replayed to the invoking terminal after the alternate-screen application exits.
- Added interactive runtime examples for sumX, Python and Bash plus HELP topics for APPEND and BROWSE.

## 0.1.3

- Added the missing always-visible IDE menu bar to the full-screen sumX source editor: File / Edit / Search / Run / Debug / Options / Help.
- F9 opens/closes the menu and F10 exits, matching the generic sumTUI editor convention.
- Menu dropdowns use sumTUI `MenuDesktop`, so they overlay the source editor rather than being clipped or hidden behind the editing panel.
- File now provides New/Open/Save/Save As; Search provides Find, next/previous search and Go to Line; Run provides Check/Run/Compile.
- Debug entries are visible but disabled until debugger execution support exists; Options exposes whitespace/control-character visualization.
- The ordinary sumX command console also gains a small top menu (File / Database / Help) with F9 Menu and F10 Exit.
- Added editor-key help and a Bash example for opening a source file in the IDE.
- sumX 0.1.3 requires sumTUI 0.5.2 or newer.

## 0.1.2

- Added optional `THEN` syntax for block IF and one-line `IF condition THEN statement`; added block `ELSE`/`ENDIF` execution and readable Python generation for IF structures.
- Added symbolic logical aliases: `&&`/AND, `||`/OR, `^^`/XOR, and `~` or `¬`/NOT.
- Made `#` the preferred/default comment introducer and added `SET AMPERSAND_COMMENT ON/OFF`; OFF is the default so `&&` normally means logical AND.
- Added `SET LINE_CONTINUATION TO BACKSLASH|SEMICOLON`; BACKSLASH is the modern default while SEMICOLON accepts very old xBase continuation-at-end-of-line source.
- Added CLI source-mode options `--line-continuation` and `--ampersand-comment` so legacy files can be parsed correctly from their first line.
- Added Fox/xBase-style `DEFINE WINDOW`, `ACTIVATE/DEACTIVATE`, `SHOW/HIDE`, and `RELEASE WINDOW`, mapped onto sumTUI positioned dialog/window primitives.
- `@ ... SAY/PRINT/GET` coordinates are relative to the active named window.
- Expanded built-in HELP and README documentation with functional examples and added runnable sumX, Python, and Bash examples.
- sumX 0.1.2 requires sumTUI 0.5.1 or newer.


## 0.1.1

- Added classic xBase `ACCEPT "Prompt" TO variable;` character input.
- Added explicit backslash physical-line continuation; a top-level semicolon always terminates the current command.
- Documented the correct multiline INPUT form with one final semicolon.
- Promoted the educational environment from the 0.1.0 alpha series to 0.1.1 and now requires sumTUI 0.5.0 or newer.

## 0.1.0a17

- Extended BASIC-like `INPUT` with `HIDDEN`, `MASK`, `WIDTH`, `HEIGHT`, `PICTURE`, `KEYS`, `DEFAULT`, `TIMEOUT`, `CASE_SENSITIVE`, and `DIALOG` options.
- Secret INPUT values no longer appear as clear text in command history; masked input records only the requested visual mask.
- INPUT choice/timeouts use sumTUI idle callbacks and can continue programs with a default value after timeout.
- `--run` and readable generated Python now reuse sumTUI's input service instead of Python's bare `input()`, preserving hidden/masked/dialog behavior and controlling-terminal semantics.
- Updated navigable INPUT help with syntax, behavior notes, and functional examples.
- README documents the companion `suminput` shell tool and the project's preference for small reusable built-in tools over unnecessary mandatory external utilities.
- README now ends with the requested `- oOo -` typography footer.
- Requires sumTUI 0.4.0a17.

## 0.1.0a16

- READ forms now leave multiline GET fields with Tab: Tab advances to the next GET and Tab on the final GET accepts READ. Enter remains a real newline inside `HEIGHT > 1` fields; Ctrl+Enter remains an optional alias when a terminal forwards it distinctly.
- When READ completes, its absolute `@ ... PRINT/SAY` + GET form is archived into ordinary command history before program execution continues. Finished fields therefore stop rendering as live highlighted controls.
- Program completion also archives any remaining coordinate screen layer, so editor Run output always returns to normal scrollable history.
- Added end-to-end regression coverage for multiline READ completion, history archival, and continued program output.
- Requires sumTUI 0.4.0a15.

## 0.1.0a14

- Added `DO program[.prg]` program execution with caller-relative path resolution and `RETURN` back to the caller.
- Added the CLI split between `sumx file.prg` (editor), `--run`, `--check`, and `--compile ... --output ...`. Generated Python is readable, executable on Unix, and intentionally depends on the sumX runtime; no standalone/native target is provided.
- Added an integrated sumTUI source editor with line numbers, save, check, run, compile and contextual F1 help (`Ctrl+F9` Run, `Alt+F9` Check).
- Reworked HELP into a navigable topic browser with F3 search and F5 Run Example. Every current help topic contains a functional example.
- Added `PRINT` as an educational alias for SAY/output, including absolute `@ row,column PRINT ...` forms.
- Added a shared PICTURE/TRANSFORM engine with character, numeric, logical and date/time pictures and modifiers including `@!`, `@Z`, `@C`, `@X`, `@(`, `@E`, `@B`, `@R`, `@K`, `@G` and `@T`.
- Added `SET FIELD_WRAP_OVERFLOW ON/OFF` (OFF by default) and use the same overflow setting for direct PICTURE output and `TRANSFORM()`.
- Extended GET with independent `WIDTH` and `HEIGHT` viewport dimensions. HEIGHT defaults to 1; HEIGHT > 1 enables multiline editing.
- Added dynamic `WCOLS()` / `WROWS()` workspace dimensions, with descriptive `SCREENCOLS()` / `SCREENROWS()` aliases.
- Added regression coverage for PICTURE overflow, GET viewport dimensions, dynamic screen dimensions, DO/RETURN, generated Python and mandatory help examples.
- Requires sumTUI 0.4.0a14.

## 0.1.0a13

- Requires sumTUI 0.4.0a13.
- Interactive command output scrollback is now reliably reachable with `PageUp` / `PageDown`.
- `Shift+PageUp` / `Shift+PageDown` remain optional aliases when the host terminal forwards them instead of consuming them.
- The `!command` shell escape from 0.1.0a12 continues to append stdout/stderr to the same scrollable command history.

## 0.1.0a12

- Added command-window shell escape: a line beginning with `!` runs the rest through the host OS shell, e.g. `!ls /`.
- Captured shell stdout/stderr is appended to the sumTUI `CommandWindow` output history, so it remains visible and can be reviewed with `Shift+PageUp` / `Shift+PageDown`.
- Plain REPL mode supports the same `!command` escape. Shell escapes are intentionally non-interactive so child processes cannot take over the TUI input stream.
- Non-zero shell exit status is shown as `[shell exit N]`.
- Requires sumTUI 0.4.0a12 or newer; that release already provides command-window scrollback and Shift+Page key decoding.

## 0.1.0a11

- Interactive `HELP` and F1 now open a scrollable/maximizable sumTUI help explorer instead of dumping the complete help text into the command window. Plain/non-TTY mode still prints help normally.
- `BROWSE` on a real table is editable: Enter or the Edit button opens the selected record in an editable `RecordForm`; SQL cursors and SQLite views remain read-only.
- `BROWSE` now carries a classic record button bar: `First | Prev | Next | Last | Search | Edit | Exit`.
- Interactive `APPEND`/record editing now carries `First | Prev | Next | Last | Search | Ok | Cancel | Exit`; `Ctrl+End` still saves and exits.
- Added record update/search/navigation support in the SQLite runtime.
- Added persistent logical relationships with `LINK table.field TO table.field AS name` and `CREATE RELATION name FROM table.field TO table.field`; `DISPLAY RELATIONS` also surfaces SQLite foreign keys.
- Added real SQLite views: `CREATE VIEW ... AS SQL.SELECT ...`, block `AS SQL ... ENDSQL`, `DISPLAY VIEWS`, and `USE view AS alias`. Views are browsable but read-only.
- Requires sumTUI 0.4.0a12 or newer.

## 0.1.0a10

- Interactive `APPEND` became an editable xBase-style record-entry dialog rather than a report/read-only view.
- Every non-autonumeric field is editable; autonumeric fields stay read-only.
- Enter/Down/Tab move through fields, Up/Shift+Tab move backward, Ctrl+End saves, Esc aborts, and F11 maximizes/restores.
- APPEND shows a compact key-hint status line inside the modal.
- Requires sumTUI 0.4.0a11 or newer.

## 0.1.0a9

- Fixed `.prg` execution on an interactive terminal: `sumx program.prg` now runs inside the sumTUI command environment instead of routing `BROWSE`/`DISPLAY` through Rich's plain table printer.
- Added a sequential TUI program runner. Program execution pauses on `BROWSE`, table dialogs, generated `APPEND`/`FORM` dialogs, and `READ`, then resumes only after the interactive operation closes or completes.
- This preserves xBase-style semantics: moving the record pointer in a table-backed `BROWSE` can affect statements that execute after the browser is closed.
- `BROWSE` in a `.prg` now opens the same sumTUI `BrowseForm` used by the interactive command window; `DISPLAY STRUCTURE` and other table results open maximizable dialogs.
- After an interactive program finishes, the sumX command window remains available, matching the dBASE/FoxPro command-environment model.
- `--plain` explicitly forces the previous textual terminal behavior; redirected/non-TTY program execution also remains textual and pipeline-friendly.
- Added regression coverage proving that later program statements do not execute until a `BROWSE`/table dialog is closed.

## 0.1.0a8

- `BROWSE` is now represented as a `BrowseRequest` and rendered by sumTUI as a real `BrowseForm`, not merely as command output.
- Moving through a table-backed `BROWSE` updates the active work-area record number and therefore the main status bar.
- `APPEND` without arguments is now always a form request (one record per form); `APPEND BLANK` remains the explicit non-interactive blank-record operation.
- Interactive `APPEND` now uses sumTUI `RecordForm`, one record per form.
- Generated APPEND forms preserve column order and show type-aware field pictures: character fields as `X`, numeric fields as `9/0` masks, dates/times as date/time pictures, logical fields as checkboxes, and AUTONUM fields as read-only `<auto>`.
- Plain mode keeps a textual fallback for `BROWSE` and prompted input for `APPEND`.
- Requires sumTUI 0.4.0a10 or newer.

## 0.1.0a7

- Added xBase-compatible `SPACE(n)` and `REPLICATE(value,n)` built-ins.
- Added `@ row,column GET variable`.
- Added combined `@ row,column SAY expression GET variable`.
- Added `READ`, backed by sumTUI absolute editable screen fields.
- Fixed-width string GETs preserve their original width, so `SPACE(30)` and `REPLICATE(" ",30)` work naturally as form buffers.
- `READ` can resume remaining statements when used in a multi-statement source block.
- Dependency bumped to `sumtui>=0.4.0a7`.

## 0.1.0a6

- Added classic xBase `@ row,column SAY expression` screen output.
- `@ SAY` accepts normal sumX expressions for row, column, and displayed value; coordinates must resolve to non-negative integers.
- Added `ScreenWriteResult` so screen-positioned output remains distinct from scrolling stdout/diagnostic messages.
- sumTUI mode routes `@ SAY` to `CommandWindow.write_at()`; plain terminal mode uses ANSI cursor addressing when attached to a TTY and a simple text fallback when redirected.
- Dependency bumped to `sumtui>=0.4.0a6` for the coordinate command-screen layer.
- `@ ... GET` / `READ` are intentionally not implemented yet.

## 0.1.0a5

- sumX Command Window now requests a `command` content style from its surrounding sumTUI `Panel`, making the entire command workspace black rather than only the rendered text rows.
- Dependency bumped to `sumtui>=0.4.0a4` for `Panel(..., content_style=...)`.
- No interpreter/database semantics changed in this release.

## 0.1.0a4

- Normal program execution is quiet by default: assignments and operational database/work-area commands no longer print unless diagnostics are enabled.
- Added `SET DEBUG_LEVEL OFF|INFO|DEBUG|TRACE`; default is `OFF`.
- Added `SET TALK ON/OFF` as an xBase-style alias for diagnostic `INFO/OFF`.
- Added CLI `--debug-level {off,info,debug,trace}`.
- Explicit output (`?`, `??`, `HELP`, `BROWSE`, `LIST`, `DISPLAY ...`, direct SQL resultsets) remains visible at the default level.
- Informational/debug messages are emitted on stderr in plain/file CLI mode; program output remains on stdout.
- sumX TUI informational messages use a muted command-window style.
- sumX table and generated record-form dialogs are maximizable with F11 when using sumTUI 0.4.0a2.
- Dependency bumped to `sumtui>=0.4.0a2`.

## 0.1.0a3

- Commands and keywords are explicitly case-insensitive.
- Added `SET CAPS_SENSITIVE ON/OFF`; it affects variable names only and defaults to OFF.
- Switching CAPS_SENSITIVE back OFF rejects ambiguous variables that differ only by case.
- Added boolean aliases `ON=TRUE=.T.` and `OFF=FALSE=.F.`.
- Added null aliases `NULL=.NULL.=NONE=NIL` plus `IS NULL` / `IS NOT NULL` expression support.
- Added `CHANNEL` as the preferred work-area command; `CHAN`, `SELECT`, `SEL`, and `SELE` are aliases.
- `USE table AS alias` is now accepted alongside `USE table ALIAS alias`.
- Work-area semantics are explicit: `USE` replaces the table in the currently selected channel.
- Status text now shows alias and underlying table (`A/1:cust=customers`).
- Added `BROW` / `BROWS` aliases for `BROWSE` and `DISP` / `STRU` compatibility abbreviations.
- Added Python-like LIST/TUPLE/DICT expressions, indexing, slicing, IN/NOT IN, safe collection methods, and indexed assignment.
- Added dynamic `OBJ(...)` values with attribute access and assignment.
- Added triple-quoted multiline strings.
- SQL is now consumable: scalar, Row, Cursor and execution-result values are returned to variables.
- Added `SQL.SELECT`, `SQL.SCALAR`, `SQL.ROW`, `SQL.CURSOR`, `SQL.EXEC`, and `SQL.QUERY` forms.
- Added `A=SQL """..."""` and `A=SQL ... ENDSQL` multiline forms.
- Added `INTO CURSOR name`; named cursors are normal runtime values and can be passed to `BROWSE`.
- Added `SumObject`, `SumRow`, `SumCursor`, `SumQuery`, and `SqlExecResult` runtime types.
- `BROWSE expression` can now display cursors, rows, lists, tuples, dictionaries and OBJ collections.
- LOGICAL schema defaults and form inputs accept ON/OFF.
- Added modern/runtime and consumable-SQL examples.

## 0.1.0a2

- `USE table ALIAS name` aliases are explicitly selectable with `SELECT name` and covered by regression tests.
- `;` is now a real optional statement terminator and can separate several sumX statements on one line.
- `#` is the preferred full-line/inline comment syntax outside quoted strings.
- Leading `*` and `&&` comments remain supported.
- `#` is reserved for comments in the sumX dialect; use `<>` or `!=` for inequality.
- Program files now use a statement splitter instead of treating trailing `;` as line continuation.
- Parenthesized multiline statements such as `CREATE TABLE (...)` continue naturally.
- TUI and plain REPL continuation prompts are now driven by open parentheses/quotes, not by `;`.

## 0.1.0a1

- First interactive sumX interpreter.
- sumTUI `CommandWindow` command shell.
- xBase boolean/operator and assignment aliases.
- SQLite-backed CREATE TABLE with sumX logical type metadata.
- 32 work areas with numeric, A-Z and alias selection; `SELECT 0` chooses a free area.
- AUTONUM, fixed NUMERIC/CURRENCY, FLOAT, MEMO(65535 chars), BLOB and other logical types.
- CREATE INDEX and SQLite REFERENCES/foreign keys.
- USE, APPEND, BROWSE, LIST, GO, SKIP, DISPLAY STRUCTURE/WORKAREAS.
- CREATE FORM FROM table + DO FORM autogenerated entry dialog.
- Raw SQL escape hatch.
- Live work-area/database status bar.

## 0.1.0a16

- sumX source editor now uses the enhanced sumTUI TextEditor selection/clipboard/undo-redo engine and preserves detected source encoding/EOL metadata through TextDocument.
- Added BASIC-like console `INPUT "Prompt" variable` (also accepts comma or `TO`) with type-aware assignment for existing variables.
- INPUT is represented as a blocking request so programs continue only after the response is accepted.
- Added INPUT help with a functional example.
