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
import re;


_SQL_BLOCK_START = re.compile(r"(?is)^(?:(?:[A-Za-z_][A-Za-z0-9_]*\s*=\s*)?SQL|CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+[A-Za-z_][A-Za-z0-9_]*\s+AS\s+SQL)$");
_SQL_BLOCK_END = re.compile(r"(?is)^\s*ENDSQL\s*;?\s*(?:#.*)?$");
_LINE_MODE = re.compile(r"(?is)^SET\s+LINE_CONTINUATION\s+(?:TO\s+)?(BACKSLASH|SEMICOLON)\s*$");
_AMP_COMMENT = re.compile(r"(?is)^SET\s+AMPERSAND_COMMENT\s+(ON|OFF|TRUE|FALSE|\.T\.|\.F\.)\s*$");


def _normalize_line_mode(value):
    key = str(value or "BACKSLASH").strip().upper();
    if key not in ("BACKSLASH", "SEMICOLON"):
        raise ValueError("LINE_CONTINUATION expects BACKSLASH or SEMICOLON");
    return key;


def _flush(buffer, statements):
    text = "".join(buffer).strip();
    buffer.clear();
    if text:
        statements.append(text);
        return text;
    return None;


def _apply_lexical_directive(statement, line_mode, ampersand_comment):
    if statement:
        match = _LINE_MODE.match(statement);
        if match:
            line_mode = match.group(1).upper();
        match = _AMP_COMMENT.match(statement);
        if match:
            ampersand_comment = match.group(1).upper() in ("ON", "TRUE", ".T.");
    return line_mode, ampersand_comment;


def _legacy_semicolon_is_continuation(text, index, ampersand_comment):
    line_end = text.find("\n", index + 1);
    if line_end < 0:
        line_end = len(text);
    tail = text[index + 1:line_end].strip();
    if not tail:
        return True;
    if tail.startswith("#"):
        return True;
    if ampersand_comment and tail.startswith("&&"):
        return True;
    return False;


def _scan(source, line_continuation="BACKSLASH", ampersand_comment=False):
    text = str(source or "");
    statements = [];
    buffer = [];
    quote = None;
    triple = False;
    escaped = False;
    paren_depth = 0;
    bracket_depth = 0;
    brace_depth = 0;
    line_has_token = False;
    sql_block = False;
    line_mode = _normalize_line_mode(line_continuation);
    amp_comment = bool(ampersand_comment);
    explicit_continuation = False;
    index = 0;
    while index < len(text):
        if sql_block:
            line_end = text.find("\n", index);
            if line_end < 0:
                line_end = len(text);
            line = text[index:line_end];
            if _SQL_BLOCK_END.match(line):
                if buffer and not buffer[-1].endswith("\n"):
                    buffer.append("\n");
                buffer.append("ENDSQL");
                flushed = _flush(buffer, statements);
                line_mode, amp_comment = _apply_lexical_directive(flushed, line_mode, amp_comment);
                sql_block = False;
            else:
                buffer.append(line);
                if line_end < len(text):
                    buffer.append("\n");
            index = line_end + (1 if line_end < len(text) else 0);
            continue;

        if quote is not None:
            if triple and text.startswith(quote, index):
                buffer.append(quote);
                index += 3;
                quote = None;
                triple = False;
                escaped = False;
                continue;
            char = text[index];
            buffer.append(char);
            if not triple:
                if escaped:
                    escaped = False;
                elif char == "\\":
                    escaped = True;
                elif char == quote:
                    quote = None;
            index += 1;
            continue;

        if text.startswith('"""', index) or text.startswith("'''", index):
            quote = text[index:index + 3];
            triple = True;
            buffer.append(quote);
            line_has_token = True;
            index += 3;
            continue;

        char = text[index];
        if char == "\\" and line_mode == "BACKSLASH":
            probe = index + 1;
            while probe < len(text) and text[probe] in (" ", "\t"):
                probe += 1;
            if probe < len(text) and text[probe] == "\n":
                if buffer and not buffer[-1].isspace():
                    buffer.append(" ");
                index = probe + 1;
                line_has_token = True;
                explicit_continuation = True;
                continue;
        if char in ("'", '"'):
            quote = char;
            triple = False;
            escaped = False;
            buffer.append(char);
            line_has_token = True;
            explicit_continuation = False;
            index += 1;
            continue;
        if char == "#":
            while index < len(text) and text[index] != "\n":
                index += 1;
            continue;
        if amp_comment and char == "&" and index + 1 < len(text) and text[index + 1] == "&":
            while index < len(text) and text[index] != "\n":
                index += 1;
            continue;
        if char == "*" and not line_has_token:
            while index < len(text) and text[index] != "\n":
                index += 1;
            continue;
        if char == "(":
            paren_depth += 1;
            buffer.append(char);
            line_has_token = True;
            explicit_continuation = False;
        elif char == ")":
            paren_depth = max(0, paren_depth - 1);
            buffer.append(char);
            line_has_token = True;
        elif char == "[":
            bracket_depth += 1;
            buffer.append(char);
            line_has_token = True;
            explicit_continuation = False;
        elif char == "]":
            bracket_depth = max(0, bracket_depth - 1);
            buffer.append(char);
            line_has_token = True;
        elif char == "{":
            brace_depth += 1;
            buffer.append(char);
            line_has_token = True;
            explicit_continuation = False;
        elif char == "}":
            brace_depth = max(0, brace_depth - 1);
            buffer.append(char);
            line_has_token = True;
        elif char == ";":
            if paren_depth == 0 and bracket_depth == 0 and brace_depth == 0:
                if line_mode == "SEMICOLON" and _legacy_semicolon_is_continuation(text, index, amp_comment):
                    if buffer and not buffer[-1].isspace():
                        buffer.append(" ");
                    line_end = text.find("\n", index + 1);
                    if line_end < 0:
                        explicit_continuation = True;
                        index = len(text);
                        continue;
                    explicit_continuation = True;
                    index = line_end + 1;
                    line_has_token = True;
                    continue;
                flushed = _flush(buffer, statements);
                line_mode, amp_comment = _apply_lexical_directive(flushed, line_mode, amp_comment);
                line_has_token = False;
                explicit_continuation = False;
            elif buffer and not buffer[-1].isspace():
                buffer.append(" ");
        elif char == "\n":
            if paren_depth == 0 and bracket_depth == 0 and brace_depth == 0:
                candidate = "".join(buffer).strip();
                if _SQL_BLOCK_START.match(candidate):
                    buffer.append("\n");
                    sql_block = True;
                else:
                    flushed = _flush(buffer, statements);
                    line_mode, amp_comment = _apply_lexical_directive(flushed, line_mode, amp_comment);
                    explicit_continuation = False;
            elif buffer and not buffer[-1].isspace():
                buffer.append(" ");
            line_has_token = False;
        else:
            buffer.append(char);
            if not char.isspace():
                line_has_token = True;
                explicit_continuation = False;
        index += 1;
    if sql_block:
        return statements, buffer, quote, triple, paren_depth, bracket_depth, brace_depth, True, explicit_continuation;
    if explicit_continuation and line_mode == "SEMICOLON":
        return statements, buffer, quote, triple, paren_depth, bracket_depth, brace_depth, False, True;
    flushed = _flush(buffer, statements);
    _apply_lexical_directive(flushed, line_mode, amp_comment);
    return statements, [], quote, triple, paren_depth, bracket_depth, brace_depth, False, False;


def split_statements(source, line_continuation="BACKSLASH", ampersand_comment=False):
    """Split sumX source into logical statements.

    Modern/default mode accepts newline or top-level ``;`` as a statement
    terminator, while a trailing ``\\`` joins the next physical line.
    Legacy ``SEMICOLON`` mode makes a semicolon at the end of a physical line
    the continuation marker; an interior semicolon still separates commands.

    ``#`` is always the preferred comment introducer. ``&&`` is a logical AND
    operator by default and becomes an inline comment introducer only when
    AMPERSAND_COMMENT compatibility mode is enabled. Leading ``*`` comments
    remain accepted for classic xBase source compatibility.
    """;
    return _scan(source, line_continuation=line_continuation, ampersand_comment=ampersand_comment)[0];


def needs_continuation(source, line_continuation="BACKSLASH", ampersand_comment=False):
    """Return True when an interactive command is structurally incomplete.""";
    text = str(source or "");
    mode = _normalize_line_mode(line_continuation);
    if mode == "BACKSLASH" and re.search(r"\\[ \t]*$", text):
        return True;
    if mode == "SEMICOLON" and re.search(r";[ \t]*(?:#.*|&&.*)?$", text):
        return True;
    if _SQL_BLOCK_START.match(text.strip()):
        return True;
    _statements, remainder, quote, _triple, parens, brackets, braces, sql_block, explicit = _scan(
        text, line_continuation=mode, ampersand_comment=ampersand_comment,
    );
    return bool(explicit or remainder or quote is not None or parens > 0 or brackets > 0 or braces > 0 or sql_block);
