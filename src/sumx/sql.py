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
import ast;
import re;

from .values import SqlExecResult, SumCursor, SumQuery, SumRow;


class SqlError(RuntimeError):
    pass;


def _strip_endsql(text):
    value = str(text).strip();
    match = re.match(r"(?is)^SQL\s*\n(.*)\n\s*ENDSQL\s*$", value);
    return match.group(1).strip() if match else None;


def parse_sql_source(source, runtime=None):
    """Parse a sumX SQL expression/statement.

    Returns (mode, sql_text). Modes: AUTO, SCALAR, ROW, CURSOR, EXEC, QUERY.
    """
    text = str(source).strip();
    if not re.match(r"(?is)^SQL\b|^SQL\.", text):
        return None;
    block = _strip_endsql(text);
    if block is not None:
        return "AUTO", block;
    tail = re.sub(r"(?is)^SQL", "", text, count=1).lstrip();
    if tail.startswith("."):
        tail = tail[1:];
        match = re.match(r"(?is)^([A-Za-z_][A-Za-z0-9_]*)\b(.*)$", tail);
        if not match:
            raise SqlError("SQL.<verb> expects SQL text");
        word = match.group(1).upper();
        rest = match.group(2).lstrip();
        if word in ("SCALAR", "ROW", "CURSOR", "EXEC", "QUERY"):
            return word, rest;
        return "AUTO", "{} {}".format(word, rest).strip();
    if tail.startswith(('"""', "'''", '"', "'")):
        try:
            value = ast.literal_eval(tail);
        except (ValueError, SyntaxError) as exc:
            raise SqlError("Invalid SQL string literal") from exc;
        return "AUTO", str(value);
    if runtime is not None and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", tail):
        try:
            value = runtime.get_value(tail);
            if isinstance(value, str):
                return "AUTO", value;
        except (NameError, KeyError):
            pass;
    return "AUTO", tail;



def strip_sumx_sql_comments(sql):
    """Remove sumX # comments from SQL while preserving quoted # data."""
    source = str(sql);
    out = [];
    quote = None;
    escaped = False;
    index = 0;
    while index < len(source):
        char = source[index];
        if quote is not None:
            out.append(char);
            if escaped:
                escaped = False;
            elif char == "\\":
                escaped = True;
            elif char == quote:
                if index + 1 < len(source) and source[index + 1] == quote:
                    out.append(source[index + 1]);
                    index += 1;
                else:
                    quote = None;
            index += 1;
            continue;
        if char in ("'", '"'):
            quote = char;
            out.append(char);
            index += 1;
            continue;
        if char == "#":
            while index < len(source) and source[index] != "\n":
                index += 1;
            continue;
        out.append(char);
        index += 1;
    return "".join(out);

def split_into_cursor(sql):
    text = str(sql).strip().rstrip(";").rstrip();
    match = re.search(r"(?is)\s+INTO\s+CURSOR\s+([A-Za-z_][A-Za-z0-9_]*)\s*$", text);
    if not match:
        return text, None;
    return text[:match.start()].rstrip(), match.group(1);


def execute_sql(runtime, sql, mode="AUTO", params=None):
    mode = str(mode or "AUTO").upper();
    sql_text, cursor_name = split_into_cursor(strip_sumx_sql_comments(sql));
    if mode == "QUERY":
        return SumQuery(runtime, sql_text);
    try:
        cursor = runtime.db.connection.execute(sql_text, params or {});
    except Exception as exc:
        raise SqlError(str(exc)) from exc;
    if cursor.description:
        columns = [item[0] for item in cursor.description];
        rows = [tuple(row) for row in cursor.fetchall()];
        result_cursor = SumCursor(columns, rows, name=cursor_name, sql=sql_text);
        if cursor_name:
            runtime.set_value(cursor_name, result_cursor);
            return result_cursor;
        if mode == "CURSOR":
            return result_cursor;
        if mode == "SCALAR":
            if len(rows) != 1 or len(columns) != 1:
                raise SqlError("SQL.SCALAR expected exactly 1 row x 1 column");
            return rows[0][0];
        if mode == "ROW":
            if len(rows) != 1:
                raise SqlError("SQL.ROW expected exactly one row");
            return SumRow(columns, rows[0]);
        if mode == "EXEC":
            raise SqlError("SQL.EXEC cannot be used with a result set");
        if len(rows) == 1 and len(columns) == 1:
            return rows[0][0];
        if len(rows) == 1:
            return SumRow(columns, rows[0]);
        return result_cursor;
    runtime.db.connection.commit();
    result = SqlExecResult(cursor.rowcount, cursor.lastrowid);
    if mode in ("SCALAR", "ROW", "CURSOR"):
        raise SqlError("SQL.{} expected a result set".format(mode));
    return result;
