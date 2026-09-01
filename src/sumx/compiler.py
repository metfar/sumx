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
from pathlib import Path;
from pprint import pformat;

from sumtui import BUILTIN_THEME_NAMES, THEMES, theme_to_dict;
import os;
import re;

from .statements import needs_continuation, split_statements;


class CompileError(ValueError):
    pass;


def check_source(source, line_continuation="BACKSLASH", ampersand_comment=False):
    text = str(source);
    if needs_continuation(text, line_continuation=line_continuation, ampersand_comment=ampersand_comment):
        raise CompileError("Source ends with an incomplete statement or block");
    statements = split_statements(text, line_continuation=line_continuation, ampersand_comment=ampersand_comment);
    _validate_if_blocks(statements);
    return statements;




def _function_header(statement):
    match = re.match(r"(?is)^(?:FUNCTION|PROCEDURE)\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s*\((.*?)\))?$", str(statement).strip());
    if match is None:
        return None;
    params = tuple(item.strip() for item in str(match.group(2) or "").split(",") if item.strip() != "");
    return match.group(1), params;


def _extract_functions(items):
    main = [];
    functions = [];
    source = list(items or []);
    index = 0;
    while index < len(source):
        statement, line_number = source[index];
        header = _function_header(statement);
        if header is None:
            main.append(source[index]);
            index += 1;
            continue;
        name, params = header;
        body = [];
        index += 1;
        while index < len(source):
            current, current_line = source[index];
            if _function_header(current) is not None:
                break;
            if str(current).strip().upper() in ("ENDFUNC", "ENDFUNCTION", "ENDPROC", "ENDPROCEDURE"):
                index += 1;
                break;
            body.append((current, current_line));
            index += 1;
        if body:
            parameter_match = re.match(r"(?is)^PARAMETERS?\s+(.+)$", str(body[0][0]).strip());
            if parameter_match is not None:
                params = tuple(item.strip() for item in parameter_match.group(1).split(",") if item.strip() != "");
                body = body[1:];
        functions.append((str(name), tuple(params), [str(item[0]) for item in body], int(line_number)));
    return main, functions;

def _statement_locations(source, statements):
    source = str(source);
    cursor = 0;
    output = [];
    for statement in statements:
        needle = str(statement).strip();
        index = source.find(needle, cursor);
        if index < 0:
            index = cursor;
        line = source.count("\n", 0, index) + 1;
        output.append((needle, line));
        cursor = max(cursor, index + max(1, len(needle)));
    return output;


def _top_level_then(text):
    source = str(text);
    quote = None;
    escaped = False;
    depth = 0;
    index = 0;
    while index < len(source):
        char = source[index];
        if quote is not None:
            if escaped:
                escaped = False;
            elif char == "\\":
                escaped = True;
            elif char == quote:
                quote = None;
            index += 1;
            continue;
        if char in ("'", '"'):
            quote = char;
            index += 1;
            continue;
        if char in "([{":
            depth += 1;
            index += 1;
            continue;
        if char in ")]}":
            depth = max(0, depth - 1);
            index += 1;
            continue;
        if depth == 0 and source[index:index + 4].upper() == "THEN":
            before = source[index - 1] if index else " ";
            after = source[index + 4] if index + 4 < len(source) else " ";
            if before.isspace() and after.isspace():
                return index, index + 4;
        index += 1;
    return None;


def _parse_if(statement):
    text = str(statement).strip();
    if not re.match(r"(?is)^IF\b", text):
        return None;
    body = re.sub(r"(?is)^IF\s+", "", text, count=1).strip();
    found = _top_level_then(body);
    if found is None:
        if not body:
            raise CompileError("IF requires a condition");
        return body, "", False;
    start, end = found;
    condition = body[:start].strip();
    tail = body[end:].strip();
    if not condition:
        raise CompileError("IF requires a condition");
    return condition, tail, bool(tail);


def _validate_if_blocks(statements):
    stack = [];
    for statement in statements:
        parsed = _parse_if(statement);
        if parsed is not None and not parsed[2]:
            stack.append(False);
            continue;
        upper = str(statement).strip().upper();
        if upper == "ELSE":
            if not stack:
                raise CompileError("Unexpected ELSE");
            if stack[-1]:
                raise CompileError("IF block contains more than one ELSE");
            stack[-1] = True;
        elif upper == "ENDIF":
            if not stack:
                raise CompileError("Unexpected ENDIF");
            stack.pop();
    if stack:
        raise CompileError("IF block requires ENDIF");
    return True;


def _emit_statement(lines, indent, statement, line_number):
    prefix = "    " * indent;
    preview = " ".join(str(statement).splitlines());
    lines.append("{}# sumX line {}: {}".format(prefix, line_number, preview));
    lines.append("{}program.statement({!r}, source_line={});".format(prefix, str(statement), line_number));


def _emit_block(items, lines, start=0, indent=0, stop_tokens=None):
    stop_tokens = set(stop_tokens or ());
    index = int(start);
    while index < len(items):
        statement, line_number = items[index];
        upper = statement.strip().upper();
        if upper in stop_tokens:
            return index, upper;
        parsed = _parse_if(statement);
        if parsed is None:
            _emit_statement(lines, indent, statement, line_number);
            index += 1;
            continue;
        condition, tail, single_line = parsed;
        prefix = "    " * indent;
        lines.append("{}# sumX line {}: {}".format(prefix, line_number, " ".join(statement.splitlines())));
        lines.append("{}if program.condition({!r}, source_line={}):".format(prefix, condition, line_number));
        if single_line:
            _emit_statement(lines, indent + 1, tail, line_number);
            index += 1;
            continue;
        branch_start = index + 1;
        branch_end, token = _emit_block(items, lines, branch_start, indent + 1, stop_tokens={"ELSE", "ENDIF"});
        if branch_end == branch_start:
            lines.append("{}    pass;".format(prefix));
        if token == "ELSE":
            lines.append("{}else:".format(prefix));
            else_start = branch_end + 1;
            endif_index, end_token = _emit_block(items, lines, else_start, indent + 1, stop_tokens={"ENDIF"});
            if endif_index == else_start:
                lines.append("{}    pass;".format(prefix));
            if end_token != "ENDIF":
                raise CompileError("IF block requires ENDIF");
            index = endif_index + 1;
        elif token == "ENDIF":
            index = branch_end + 1;
        else:
            raise CompileError("IF block requires ENDIF");
    return index, None;


def compile_source(source, source_name="<program>", line_continuation="BACKSLASH", ampersand_comment=False, theme="XBASE"):
    statements = check_source(source, line_continuation=line_continuation, ampersand_comment=ampersand_comment);
    items = _statement_locations(source, statements);
    items, functions = _extract_functions(items);
    selected_theme = theme if theme in THEMES else "XBASE";
    if selected_theme in BUILTIN_THEME_NAMES:
        theme_name = selected_theme;
        theme_data = None;
    else:
        theme_name = None;
        theme_data = theme_to_dict(THEMES[selected_theme]);
    lines = [
        "#!/usr/bin/env python3",
        "# -*- coding: utf-8 -*-",
        "# Generated by sumX. This file intentionally depends on the sumX runtime.",
        "# The generated form stays readable so students can inspect the translation.",
        "# Compile-time theme: {}".format(selected_theme),
        "",
        "from sumx.compiler_support import GeneratedProgram;",
        "",
        "PROGRAM_THEME_NAME = {!r};".format(theme_name),
        "PROGRAM_THEME_DATA = {};".format(pformat(theme_data, width=100, sort_dicts=True)),
        "",
        "program = GeneratedProgram(source_name={!r}, theme_name=PROGRAM_THEME_NAME, theme_data=PROGRAM_THEME_DATA);".format(str(source_name)),
        "program.interpreter.runtime.set_line_continuation({!r});".format(str(line_continuation).upper()),
        "program.interpreter.runtime.set_ampersand_comment({});".format("True" if ampersand_comment else "False"),
        "",
    ];
    for name, params, body, line_number in functions:
        lines.append("program.define_function({!r}, {!r}, {!r}, source_line={});".format(name, params, body, line_number));
    if functions:
        lines.append("");
    _emit_block(items, lines, start=0, indent=0);
    lines.append("");
    lines.append("raise SystemExit(program.finish());");
    lines.append("");
    return "\n".join(lines);


def compile_file(path, output=None, line_continuation="BACKSLASH", ampersand_comment=False, theme="XBASE"):
    source_path = Path(path).expanduser().resolve();
    source = source_path.read_text(encoding="utf-8", errors="replace");
    generated = compile_source(
        source,
        source_name=str(source_path),
        line_continuation=line_continuation,
        ampersand_comment=ampersand_comment,
        theme=theme,
    );
    if output == "-":
        return generated, None;
    output_path = Path(output).expanduser() if output else source_path.with_suffix(".py");
    output_path.write_text(generated, encoding="utf-8");
    try:
        mode = output_path.stat().st_mode;
        output_path.chmod(mode | 0o111);
    except OSError:
        pass;
    return generated, output_path;
