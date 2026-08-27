#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#pylint:disable=W0301
#  
#  Copyright 2018- William Martinez Bas <metfar@gmail.com>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#
#import warnings;
#warnings.filterwarnings("ignore", category=UserWarning);
from dataclasses import dataclass;


@dataclass(frozen=True)
class HelpTopic:
    name: str;
    category: str;
    summary: str;
    syntax: tuple;
    example: str;
    notes: tuple = tuple();
    see_also: tuple = tuple();

    def markdown(self):
        lines = ["# {}".format(self.name), "", self.summary, "", "## Syntax", ""];
        lines.append("```text");
        lines.extend(self.syntax);
        lines.append("```");
        if self.notes:
            lines.extend(["", "## Notes", ""]);
            lines.extend(["- {}".format(item) for item in self.notes]);
        lines.extend(["", "## Functional example", "", "```xbase"]);
        lines.extend(self.example.rstrip().splitlines());
        lines.append("```");
        if self.see_also:
            lines.extend(["", "## See also", "", ", ".join(self.see_also)]);
        return "\n".join(lines);


_TOPICS = [
    HelpTopic(
        "DO", "Programming", "Executes another sumX program file (.PRG).",
        ("DO program", "DO path/to/program.prg"),
        'PRINT "Before"\nDO examples/hello\nPRINT "After"',
        ("The .prg extension is optional.", "Relative paths are resolved from the calling program first."),
        ("RETURN", "--run"),
    ),
    HelpTopic(
        "RETURN", "Programming", "Stops the current program file and returns to its caller.",
        ("RETURN",),
        'PRINT "This is printed"\nRETURN\nPRINT "This is not printed"',
        see_also=("DO",),
    ),
    HelpTopic(
        "IF", "Programming", "Conditionally executes one statement or a block; THEN is optional for block form.",
        (
            "IF condition THEN statement",
            "IF condition\n    statements\nENDIF",
            "IF condition THEN\n    statements\n[ELSE\n    statements]\nENDIF",
        ),
        'a = 5\nIF a == 5 THEN PRINT "single line"\nIF a == 5 THEN\n    PRINT "block line 1"\n    PRINT "block line 2"\nENDIF',
        ("A one-line IF with code after THEN does not require ENDIF.", "IF ... THEN with THEN at the end of the logical line starts a block."),
        ("LOGICAL OPERATORS",),
    ),
    HelpTopic(
        "LOGICAL OPERATORS", "Programming", "Boolean operators have keyword and symbolic spellings.",
        ("AND / &&", "OR / ||", "XOR / ^^", "NOT / ~ / ¬"),
        'ready = ON\nenabled = OFF\n? ready && ~enabled\n? ready || enabled\n? ready ^^ enabled',
        ("# is the default comment introducer.", "SET AMPERSAND_COMMENT ON reassigns && to classic xBase inline-comment syntax; AND remains available."),
        ("IF", "SET AMPERSAND_COMMENT"),
    ),
    HelpTopic(
        "SET AMPERSAND_COMMENT", "Settings", "Chooses whether && means logical AND or a classic xBase inline comment.",
        ("SET AMPERSAND_COMMENT OFF", "SET AMPERSAND_COMMENT ON"),
        'SET AMPERSAND_COMMENT OFF\n? ON && ON\nSET AMPERSAND_COMMENT ON\nA = 5 && this text is now a comment\n? A',
        ("OFF is the default, so && is normally AND.", "# remains the preferred/default comment marker in both modes."),
        ("LOGICAL OPERATORS",),
    ),
    HelpTopic(
        "SET LINE_CONTINUATION", "Settings", "Selects the physical-line continuation convention used by the source reader.",
        ("SET LINE_CONTINUATION TO BACKSLASH", "SET LINE_CONTINUATION TO SEMICOLON"),
        'SET LINE_CONTINUATION TO SEMICOLON\nINPUT "Continue?" answer ;\n    KEYS "YN" ;\n    DEFAULT "N" ;\n    DIALOG\nSET LINE_CONTINUATION TO BACKSLASH',
        ("BACKSLASH is the modern/default mode: newline or ; ends a statement and trailing \\ continues it.", "SEMICOLON compatibility mode treats a semicolon at the end of a physical line as continuation; interior semicolons still separate statements."),
        ("INPUT",),
    ),
    HelpTopic(
        "DEFINE WINDOW", "Screen I/O", "Defines a Fox/xBase-style named window backed by a sumTUI dialog/window primitive.",
        (
            "DEFINE WINDOW name FROM row,col TO row,col [TITLE text] [SHADOW] [PANEL] [COLOR SCHEME n]",
            "ACTIVATE WINDOW name",
            "DEACTIVATE WINDOW [name]",
            "RELEASE WINDOW name",
        ),
        'answer = "N"\nDEFINE WINDOW wDialogo FROM 4,10 TO 12,55 TITLE " Confirmación " SHADOW PANEL COLOR SCHEME 5\nACTIVATE WINDOW wDialogo\n@ 1,2 PRINT "¿Continuar?"\n@ 3,2 GET answer WIDTH 1 PICTURE "@! A"\nREAD\nDEACTIVATE WINDOW wDialogo\nRELEASE WINDOW wDialogo\nPRINT answer',
        ("@ row,column coordinates are relative to the active window while it is active.", "SHOW/HIDE WINDOW are accepted as ACTIVATE/DEACTIVATE aliases."),
        ("GET", "READ"),
    ),
    HelpTopic(
        "APPEND", "Database", "Adds a record to the active table; without values it opens the interactive record form when a TUI runtime is available.",
        ("APPEND", "APPEND BLANK", "APPEND field=expression [, field=expression ...]"),
        'CREATE TABLE demo (id AUTONUM, name VARCHAR(30))\nUSE demo\nAPPEND\nBROWSE',
        ("sumx --run program.prg keeps this interactive form available without opening the IDE.", "sumx --plain --run program.prg uses textual prompts instead."),
        ("BROWSE",),
    ),
    HelpTopic(
        "BROWSE", "Database", "Opens an interactive table browser for the active table or displays a browsable expression/cursor.",
        ("BROWSE", "BROW", "BROWSE expression [LIMIT n]"),
        'CREATE TABLE demo (id AUTONUM, name VARCHAR(30))\nUSE demo\nAPPEND name="Ana"\nAPPEND name="Luis"\nBROWSE',
        ("In interactive --run mode the browser is a sumTUI modal and program execution resumes after it closes.", "Table-backed BROWSE includes New* to append a record directly and then refresh the browser.", "Views and expression/cursor results may be read-only."),
        ("APPEND",),
    ),
    HelpTopic(
        "PRINT", "Screen I/O", "sumX alias for SAY/output, provided as a familiar educational spelling.",
        ("PRINT expression [PICTURE picture]", "@ row,column PRINT expression [PICTURE picture]", "@ row,column PRINT expression GET variable [...]"),
        'name = "Ana"\nPRINT "Hello " + name\nPRINT 1250.50 PICTURE "$999,999.99"',
        ("Classic ? and SAY forms remain available.",),
        ("SAY", "PICTURE", "TRANSFORM"),
    ),
    HelpTopic(
        "PICTURE", "Formatting", "Formats output and defines GET input/display masks.",
        ("? expression PICTURE picture", "PRINT expression PICTURE picture", "@ row,column SAY expression PICTURE picture", "GET variable PICTURE picture"),
        'nValue = 1250.50\n? nValue PICTURE "$999,999.99"\n? "usuario12" PICTURE "@! NNNNNNNN"',
        ("A/N/X/!/9/#/Y/L are editable mask positions.", "@!, @Z, @C, @X, @(, @E, @B, @R, @K, @G and @T are supported modifiers."),
        ("TRANSFORM", "SET FIELD_WRAP_OVERFLOW", "GET"),
    ),
    HelpTopic(
        "TRANSFORM", "Formatting", "Returns the formatted representation of a value using the same PICTURE engine as output and GET.",
        ("TRANSFORM(value, picture)",),
        'cFormatted = TRANSFORM(1250.50, "$999,999.99")\nPRINT cFormatted\n? TRANSFORM("usuario12", "@! NNNNNNNN")',
        see_also=("PICTURE", "SET FIELD_WRAP_OVERFLOW"),
    ),
    HelpTopic(
        "SET FIELD_WRAP_OVERFLOW", "Settings", "Controls whether values may continue beyond the logical PICTURE mask.",
        ("SET FIELD_WRAP_OVERFLOW OFF", "SET FIELD_WRAP_OVERFLOW ON"),
        'SET FIELD_WRAP_OVERFLOW OFF\n? TRANSFORM("usuario12", "NNNNNNNN")\nSET FIELD_WRAP_OVERFLOW ON\n? TRANSFORM("usuario12", "NNNNNNNN")',
        ("OFF is the default.", "WIDTH and HEIGHT are display viewport dimensions and are independent of this setting."),
        ("PICTURE", "GET"),
    ),
    HelpTopic(
        "GET", "Screen I/O", "Defines an editable field at an absolute screen coordinate.",
        ("@ row,column GET variable [WIDTH n] [HEIGHT n] [PICTURE picture]", "@ row,column SAY expression GET variable [WIDTH n] [HEIGHT n] [PICTURE picture]"),
        'notes = "Edit this text"\n@ 2,2 SAY "Notes:"\n@ 3,2 GET notes WIDTH 30 HEIGHT 4\nREAD\nPRINT notes',
        ("WIDTH is visible columns only.", "HEIGHT defaults to 1; HEIGHT > 1 is a multiline textarea-like field.", "Tab moves to the next GET; Tab on the last GET accepts READ."),
        ("READ", "PICTURE"),
    ),
    HelpTopic(
        "READ", "Screen I/O", "Activates pending GET fields and writes accepted values back to their variables.",
        ("READ",),
        'name = SPACE(20)\n@ 2,2 SAY "Name:" GET name WIDTH 12\nREAD\nPRINT name',
        see_also=("GET",),
    ),
    HelpTopic(
        "ACCEPT", "Console I/O", "Reads a character response using the classic xBase ACCEPT ... TO syntax.",
        ('ACCEPT "Prompt" TO variable',),
        'ACCEPT "Por favor, ingresa tu nombre: " TO cNombre;\nPRINT cNombre;',
        ("ACCEPT always stores character text, even when the target variable previously contained another type.",),
        ("INPUT", "PRINT"),
    ),
    HelpTopic(
        "INPUT", "Console I/O", "Reads a console response into a variable using a BASIC-like educational syntax.",
        (
            'INPUT "Prompt" variable',
            'INPUT "Prompt" variable WIDTH n [HEIGHT n]',
            'INPUT "Prompt" variable PICTURE picture',
            'INPUT "Prompt" variable HIDDEN',
            'INPUT "Prompt" variable MASK "*"',
            'INPUT "Prompt" variable KEYS "YN" [DEFAULT "N"] [TIMEOUT 10] [CASE_SENSITIVE] [DIALOG]',
            'INPUT "Prompt" variable \\  ... \\  DIALOG ;',
        ),
        'INPUT "Continue?" answer \\n    KEYS "YN" \\n    DEFAULT "N" \\n    TIMEOUT 10 \\n    DIALOG ;\nPRINT answer;',
        (
            "If the target already exists, sumX converts the response to its current logical/numeric type when possible.",
            "A new target is created as character text.",
            "HIDDEN echoes nothing; MASK repeats only the supplied visual mask per entered character.",
            "WIDTH/HEIGHT are presentation dimensions; PICTURE remains an input/format mask.",
            "KEYS provides DOS CHOICE-style one-key input; DEFAULT and TIMEOUT support unattended input.",
            "By default, newline or a top-level semicolon ends the command; a trailing backslash continues the logical line. SET LINE_CONTINUATION TO SEMICOLON enables legacy semicolon-at-EOL continuation.",
            "Multiline INPUT currently does not combine with HIDDEN, MASK, KEYS or PICTURE.",
        ),
        ("ACCEPT", "GET", "READ", "PRINT", "PICTURE"),
    ),
    HelpTopic(
        "WCOLS", "Environment", "Returns the number of visible columns in the current sumX command workspace.",
        ("WCOLS()",),
        '? WCOLS()',
        ("In plain mode it falls back to the terminal width.", "SCREENCOLS() is a descriptive alias."),
        ("WROWS",),
    ),
    HelpTopic(
        "WROWS", "Environment", "Returns the number of visible rows in the current sumX command workspace.",
        ("WROWS()",),
        '? WROWS()',
        ("In plain mode it falls back to the terminal height.", "SCREENROWS() is a descriptive alias."),
        ("WCOLS",),
    ),
    HelpTopic(
        "SHELL ESCAPE", "Environment", "Runs a non-interactive operating-system shell command and keeps its output in command history.",
        ("!command",),
        '!printf "hello from the shell\\n"',
        see_also=("DO",),
    ),
];

TOPICS = {topic.name.upper(): topic for topic in _TOPICS};
ALIASES = {
    "FIELD_WRAP_OVERFLOW": "SET FIELD_WRAP_OVERFLOW",
    "SET FIELD WRAP OVERFLOW": "SET FIELD_WRAP_OVERFLOW",
    "AMPERSAND_COMMENT": "SET AMPERSAND_COMMENT",
    "LINE_CONTINUATION": "SET LINE_CONTINUATION",
    "WINDOW": "DEFINE WINDOW",
    "SCREENCOLS": "WCOLS",
    "SCREENROWS": "WROWS",
    "!": "SHELL ESCAPE",
};


def topic_names():
    return [topic.name for topic in sorted(_TOPICS, key=lambda item: (item.category, item.name))];


def find_topic(name):
    raw = str(name or "").strip().upper();
    raw = ALIASES.get(raw, raw);
    if raw in TOPICS:
        return TOPICS[raw];
    matches = [topic for key, topic in TOPICS.items() if key.startswith(raw)] if raw else [];
    return matches[0] if len(matches) == 1 else None;


def index_markdown():
    lines = ["# sumX Help", "", "Every documented language feature includes a functional example.", ""];
    categories = {};
    for topic in sorted(_TOPICS, key=lambda item: (item.category, item.name)):
        categories.setdefault(topic.category, []).append(topic);
    for category, topics in categories.items():
        lines.extend(["## {}".format(category), ""]);
        for topic in topics:
            lines.append("- **{}** — {}".format(topic.name, topic.summary));
        lines.append("");
    return "\n".join(lines).rstrip();
