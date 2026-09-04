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
from decimal import Decimal;
from pathlib import Path;

from .database import split_top_level;
from .expressions import ExpressionEvaluator;
from .helpdb import find_topic, index_markdown;
from .picture import parse_picture, picture_capacity, picture_choices, picture_display_width, strip_picture_literals, transform;
from .results import AppendRequest, BatchResult, BrowseRequest, ClearResult, FormRequest, GetField, HelpRequest, InputRequest, OutputResult, QuitResult, ReadRequest, ReturnResult, ScreenGetResult, ScreenWriteResult, TableResult, WindowRequest;
from .runtime import Runtime;
from .sql import parse_sql_source;
from .statements import split_statements;
from .values import SqlExecResult, SumCursor, SumObject, SumQuery, SumRow, display_value, tabularize;


class SumXError(RuntimeError):
    pass;


HELP_TEXT = '''sumX 0.1 command window

Assignments and values:
  STORE 5 TO A
  LET A = 5
  A = 5
  ON = TRUE = .T.    OFF = FALSE = .F.
  NULL = .NULL. = NONE = NIL
  A = [10, 20, 30]
  P = {"name": "Ana", "active": ON}
  O = OBJ(name="Ana", phones=["123", "456"])
  ? O.name

Variable names:
  SET CAPS_SENSITIVE OFF   (default: variables ignore case)
  SET CAPS_SENSITIVE ON    (variables become case-sensitive)
  Commands/keywords are always case-insensitive.

Output / diagnostics:
  SET DEBUG_LEVEL OFF       (default; program output only)
  SET DEBUG_LEVEL INFO      (show command/assignment information)
  SET DEBUG_LEVEL DEBUG     (reserved for deeper diagnostics)
  SET DEBUG_LEVEL TRACE     (reserved for parser/runtime tracing)
  SET TALK ON/OFF           (xBase-style alias for INFO/OFF)
  SET CONFIRM ON/OFF        (stay in bounded GET / auto-advance at logical end)

Statement syntax:
  ; terminates a statement; a trailing \\ joins the next physical line
  # comment (full-line or inline)
  && comment and leading * comments remain accepted
  Multiple statements can share one line: A=1; B=2; ? A+B;

Work areas / channels:
  USE customers AS cust
  CHANNEL 2
  CHAN 2
  SELECT 2 / SEL 2        (xBase compatibility)
  CHANNEL cust            (select the channel holding alias cust)
  CHANNEL 0               (next free channel)
  USE another             (replaces the table in the active channel)

Database:
  CREATE TABLE name (id AUTONUM, name VARCHAR(80), notes MEMO)
  CREATE INDEX idx ON table(column)
  LINK customers.id TO sales.customer_id AS customer_sales
  CREATE RELATION customer_sales FROM customers.id TO sales.customer_id
  DISPLAY RELATIONS
  CREATE VIEW totals AS SQL.SELECT customer_id,SUM(total) total FROM sales GROUP BY customer_id
  DISPLAY VIEWS
  CREATE FORM formname FROM table
  OPEN DATABASE file.sqlite
  APPEND
  APPEND BLANK
  APPEND name="Ana", active=ON
  BROWSE / BROW
  BROWSE variable
  GO TOP | GO BOTTOM | GO n
  SKIP [n]
  DISPLAY STRUCTURE
  DISPLAY WORKAREAS
  SET RELATION TO field INTO area [ON target_field]

Real SQLite SQL:
  A = SQL.SELECT count(*) FROM customers;
  A = SQL """SELECT id, name FROM customers;""";
  A = SQL
      SELECT id, name FROM customers
      INTO CURSOR people
  ENDSQL;
  SQL.SELECT id, name FROM customers;
  SQL.SCALAR SELECT count(*) FROM customers;
  SQL.ROW SELECT id, name FROM customers WHERE id=1;
  SQL.CURSOR SELECT id, name FROM customers;
  SQL.EXEC UPDATE customers SET active=0;

Screen I/O:
  SPACE(n) / REPLICATE(text,n)
  @ row,column SAY expression
  @ row,column GET variable
  @ row,column SAY expression GET variable
  READ
  DEFINE WINDOW w FROM r1,c1 TO r2,c2 TITLE "Title" SHADOW PANEL COLOR SCHEME 5
  ACTIVATE WINDOW w / DEACTIVATE WINDOW w / RELEASE WINDOW w
  INPUT "Prompt" variable      read typed console input into a variable
  ACCEPT "Prompt" TO variable  read a character response into a variable
  Coordinates are zero-based, as in classic xBase screen commands.

Shell escape:
  !ls /                     run a non-interactive OS shell command
  !pwd
  Shell output is appended to command-window history.

TUI navigation:
  HELP / F1                 opens the help explorer
  PageUp/PageDown           command-window output scrollback
  Shift+PageUp/PageDown     alias when terminal forwards it
  F11                       maximize/restore dialogs

General:
  ? expression
  ?? expression
  CLEAR
  HELP
  QUIT
''';


class Interpreter:
    def __init__(self, runtime=None, database=":memory:"):
        self.runtime = runtime or Runtime(database=database);
        self.expr = ExpressionEvaluator(self.runtime);
        self.pending_gets = [];
        self.source_stack = [];
        self.user_functions = {};
        self.runtime._user_function_handler = self._call_user_function;

    @staticmethod
    def _function_header(statement):
        match = re.match(r"(?is)^(?:FUNCTION|PROCEDURE)\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s*\((.*?)\))?$", str(statement).strip());
        if match is None:
            return None;
        params = tuple(item.strip() for item in split_top_level(match.group(2) or "", ",") if item.strip() != "");
        return match.group(1), params;

    def prepare_statements(self, statements):
        source = list(statements or []);
        main = [];
        index = 0;
        while index < len(source):
            header = self._function_header(source[index]);
            if header is None:
                main.append(source[index]);
                index += 1;
                continue;
            name, params = header;
            body = [];
            index += 1;
            while index < len(source):
                current = str(source[index]).strip();
                if self._function_header(current) is not None:
                    break;
                if current.upper() in ("ENDFUNC", "ENDFUNCTION", "ENDPROC", "ENDPROCEDURE"):
                    index += 1;
                    break;
                body.append(source[index]);
                index += 1;
            if body:
                parameter_match = re.match(r"(?is)^PARAMETERS?\s+(.+)$", str(body[0]).strip());
                if parameter_match is not None:
                    params = tuple(item.strip() for item in split_top_level(parameter_match.group(1), ",") if item.strip() != "");
                    body = body[1:];
            self.user_functions[str(name).casefold()] = {"name": str(name), "params": tuple(params), "body": list(body)};
        return main;

    def _execute_function_body(self, statements):
        work = list(statements or []);
        index = 0;
        while index < len(work):
            statement = str(work[index]).strip();
            parsed_if = self._parse_if_statement(statement);
            if parsed_if is not None:
                condition, tail, single_line = parsed_if;
                if single_line:
                    if bool(self.evaluate(condition)):
                        work[index] = tail;
                    else:
                        del work[index];
                    continue;
                else_index, endif_index = self._find_if_block(work, index);
                selected = bool(self.evaluate(condition));
                if selected:
                    branch_end = else_index if else_index is not None else endif_index;
                    branch = work[index + 1:branch_end];
                else:
                    branch = work[else_index + 1:endif_index] if else_index is not None else [];
                work[index:endif_index + 1] = branch;
                continue;
            if statement.upper() in ("ELSE", "ENDIF"):
                raise SumXError("Unexpected {}".format(statement.upper()));
            return_match = re.match(r"(?is)^RETURN(?:\s+(.+))?$", statement);
            if return_match is not None:
                expression = (return_match.group(1) or "").strip();
                return True, (self.evaluate(expression) if expression else None);
            if re.match(r"(?is)^PARAMETERS?\s+", statement):
                index += 1;
                continue;
            result = self._execute_one(statement, interactive=False);
            if isinstance(result, ReturnResult):
                return True, result.value;
            if isinstance(result, (ReadRequest, InputRequest, AppendRequest, FormRequest, BrowseRequest, HelpRequest, WindowRequest)):
                raise SumXError("Interactive operation is not allowed inside expression function {}".format(statement));
            index += 1;
        return False, None;

    def _call_user_function(self, name, args):
        key = str(name).casefold();
        if key not in self.user_functions:
            raise KeyError(name);
        function = self.user_functions[key];
        params = tuple(function["params"]);
        if len(args) != len(params):
            raise SumXError("{} expects {} argument(s), got {}".format(function["name"], len(params), len(args)));
        saved = [];
        for parameter, value in zip(params, args):
            existing = self.runtime._find_variable_name(parameter);
            if existing is None:
                saved.append((parameter, None, None));
            else:
                saved.append((parameter, existing, self.runtime.variables[existing]));
            self.runtime.set_value(parameter, value);
        try:
            _returned, value = self._execute_function_body(function["body"]);
            return value;
        finally:
            for parameter, existing, value in reversed(saved):
                current = self.runtime._find_variable_name(parameter);
                if existing is None:
                    if current is not None:
                        del self.runtime.variables[current];
                else:
                    if current is not None and current != existing:
                        del self.runtime.variables[current];
                    self.runtime.variables[existing] = value;

    def evaluate(self, expression):
        return self.expr.evaluate(expression);

    def _parse_if_statement(self, statement):
        text = str(statement).strip();
        if not re.match(r"(?is)^IF\b", text):
            return None;
        body = re.sub(r"(?is)^IF\s+", "", text, count=1).strip();
        positions = self._clause_positions(body, ("THEN",));
        if positions:
            index, _keyword, end = positions[0];
            condition = body[:index].strip();
            tail = body[end:].strip();
            if not condition:
                raise SumXError("IF requires a condition");
            return condition, tail, bool(tail);
        if not body:
            raise SumXError("IF requires a condition");
        return body, "", False;

    def _find_if_block(self, statements, start):
        depth = 0;
        else_index = None;
        for index in range(start + 1, len(statements)):
            statement = str(statements[index]).strip();
            parsed = self._parse_if_statement(statement);
            if parsed is not None and not parsed[2]:
                depth += 1;
                continue;
            upper = statement.upper();
            if upper == "ENDIF":
                if depth == 0:
                    return else_index, index;
                depth -= 1;
                continue;
            if upper == "ELSE" and depth == 0:
                if else_index is not None:
                    raise SumXError("IF block contains more than one ELSE");
                else_index = index;
        raise SumXError("IF block requires ENDIF");

    def execute_many(self, source, interactive=True):
        statements = list(split_statements(
            source,
            line_continuation=self.runtime.line_continuation,
            ampersand_comment=self.runtime.ampersand_comment,
        ));
        statements = self.prepare_statements(statements);
        results = [];
        index = 0;
        while index < len(statements):
            statement = str(statements[index]).strip();
            parsed_if = self._parse_if_statement(statement);
            if parsed_if is not None:
                condition, tail, single_line = parsed_if;
                if single_line:
                    if bool(self.evaluate(condition)):
                        statements[index] = tail;
                    else:
                        del statements[index];
                    continue;
                else_index, endif_index = self._find_if_block(statements, index);
                selected = bool(self.evaluate(condition));
                if selected:
                    branch_end = else_index if else_index is not None else endif_index;
                    branch = statements[index + 1:branch_end];
                else:
                    branch = statements[else_index + 1:endif_index] if else_index is not None else [];
                statements[index:endif_index + 1] = branch;
                continue;
            if statement.upper() in ("ELSE", "ENDIF"):
                raise SumXError("Unexpected {}".format(statement.upper()));
            result = self._execute_one(statement, interactive=interactive);
            if result is not None:
                if isinstance(result, (ReadRequest, InputRequest)):
                    result.remaining = statements[index + 1:];
                results.append(result);
            if isinstance(result, (QuitResult, ReturnResult, ReadRequest, InputRequest)):
                break;
            index += 1;
        return results;

    def execute_remaining(self, statements, interactive=True):
        if not statements:
            return None;
        return self.execute("\n".join(str(item) for item in statements), interactive=interactive);

    def execute(self, source, interactive=True):
        results = self.execute_many(source, interactive=interactive);
        if not results:
            return None;
        if len(results) == 1:
            return results[0];
        return BatchResult(results);

    def _output(self, text):
        return OutputResult(str(text), level="OUTPUT", channel="stdout", emit=True);

    def _message(self, text, level="INFO"):
        level = str(level).strip().upper();
        return OutputResult(str(text), level=level, channel="stderr", emit=self.runtime.debug_enabled(level));

    def _result_for_value(self, value, title="Value"):
        if isinstance(value, SqlExecResult):
            return self._message("SQL OK ({} rows affected)".format(value.rowcount), level="INFO");
        if isinstance(value, SumQuery):
            return self._output(repr(value));
        if isinstance(value, (SumCursor, SumRow, SumObject, dict, list, tuple)):
            columns, rows = tabularize(value);
            return TableResult(title, columns, rows);
        return self._output(display_value(value));

    def _assign_target(self, target, value):
        raw = str(target).strip();
        try:
            node = ast.parse(raw, mode="eval").body;
        except SyntaxError as exc:
            raise SumXError("Invalid assignment target: {}".format(target)) from exc;
        if isinstance(node, ast.Name):
            self.runtime.set_value(node.id, value);
            return value;
        if isinstance(node, ast.Subscript):
            container = self.expr._eval(node.value);
            key = self.expr._eval_slice(node.slice);
            try:
                container[key] = value;
            except Exception as exc:
                raise SumXError("Cannot assign to {}".format(target)) from exc;
            return value;
        if isinstance(node, ast.Attribute):
            container = self.expr._eval(node.value);
            if not isinstance(container, SumObject):
                raise SumXError("Attribute assignment is only available on OBJ values");
            setattr(container, node.attr, value);
            return value;
        raise SumXError("Unsupported assignment target: {}".format(target));

    def _execute_sql_value(self, sql_source):
        parsed = parse_sql_source(sql_source, runtime=self.runtime);
        if parsed is None:
            raise SumXError("Invalid SQL expression");
        mode, sql_text = parsed;
        return self.runtime.execute_sql(sql_text, mode=mode);

    @staticmethod
    def _coord(value, label):
        if isinstance(value, bool):
            raise SumXError("{} must be an integer coordinate".format(label));
        try:
            number = int(value);
        except (TypeError, ValueError) as exc:
            raise SumXError("{} must be an integer coordinate".format(label)) from exc;
        if number < 0 or value != number:
            raise SumXError("{} must be an integer coordinate >= 0".format(label));
        return number;

    @staticmethod
    def _split_get_clause(text):
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
            if depth == 0 and source[index:index + 3].upper() == "GET":
                before = source[index - 1] if index else " ";
                after = source[index + 3] if index + 3 < len(source) else " ";
                if before.isspace() and after.isspace():
                    return source[:index].strip(), source[index + 3:].strip();
            index += 1;
        return source.strip(), None;

    @staticmethod
    def _clause_positions(text, keywords):
        source = str(text);
        wanted = sorted([str(item).upper() for item in keywords], key=len, reverse=True);
        output = [];
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
            if depth == 0:
                for keyword in wanted:
                    end = index + len(keyword);
                    if source[index:end].upper() != keyword:
                        continue;
                    before = source[index - 1] if index else " ";
                    after = source[end] if end < len(source) else " ";
                    if before.isspace() and after.isspace():
                        output.append((index, keyword, end));
                        index = end;
                        break;
                else:
                    index += 1;
                    continue;
                continue;
            index += 1;
        return output;

    def _split_picture_clause(self, text):
        source = str(text).strip();
        positions = self._clause_positions(source, ("PICTURE",));
        if not positions:
            return source, None;
        index, _keyword, end = positions[-1];
        expression = source[:index].strip();
        picture = source[end:].strip();
        if not expression or not picture:
            raise SumXError("PICTURE requires both a value and a picture expression");
        return expression, picture;

    def _parse_get_clause(self, text):
        source = str(text).strip();
        positions = self._clause_positions(source, ("WIDTH", "HEIGHT", "PICTURE", "VALID", "ERROR"));
        first = positions[0][0] if positions else len(source);
        target = source[:first].strip();
        if not target:
            raise SumXError("GET requires a variable or assignable target");
        options = {};
        for number, (index, keyword, end) in enumerate(positions):
            next_index = positions[number + 1][0] if number + 1 < len(positions) else len(source);
            value = source[end:next_index].strip();
            if not value:
                raise SumXError("GET {} requires a value".format(keyword));
            if keyword in options:
                raise SumXError("GET {} specified more than once".format(keyword));
            options[keyword] = value;
        width = None;
        height = 1;
        picture = "";
        valid = "";
        error = "";
        if "WIDTH" in options:
            width = self._coord(self.evaluate(options["WIDTH"]), "GET WIDTH");
            if width <= 0:
                raise SumXError("GET WIDTH must be >= 1");
        if "HEIGHT" in options:
            height = self._coord(self.evaluate(options["HEIGHT"]), "GET HEIGHT");
            if height <= 0:
                raise SumXError("GET HEIGHT must be >= 1");
        if "PICTURE" in options:
            picture = self.evaluate(options["PICTURE"]);
            if not isinstance(picture, str):
                raise SumXError("GET PICTURE must evaluate to a string");
        if "VALID" in options:
            valid = str(options["VALID"]).strip();
        if "ERROR" in options:
            error_value = self.evaluate(options["ERROR"]);
            error = str(error_value);
        layout_options = any(key in options for key in ("WIDTH", "HEIGHT", "PICTURE"));
        return target, width, height, picture, valid, error, bool(layout_options);

    def _format_expression(self, expression, picture_expression=None):
        value = self.evaluate(expression);
        if picture_expression is None:
            return display_value(value);
        picture = self.evaluate(picture_expression);
        if not isinstance(picture, str):
            raise SumXError("PICTURE must evaluate to a string");
        return transform(value, picture, overflow=self.runtime.field_wrap_overflow);

    def _resolve_program_path(self, value):
        raw = str(value).strip();
        if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
            raw = raw[1:-1];
        path = Path(raw).expanduser();
        candidates = [];
        if path.is_absolute():
            candidates.append(path);
        else:
            if self.source_stack:
                candidates.append(self.source_stack[-1].parent / path);
            candidates.append(Path.cwd() / path);
        expanded = [];
        for candidate in candidates:
            expanded.append(candidate);
            if candidate.suffix == "":
                expanded.append(candidate.with_suffix(".prg"));
        for candidate in expanded:
            if candidate.is_file():
                return candidate.resolve();
        raise SumXError("Program not found: {}".format(raw));

    def _make_get_field(self, target, row, column, width=None, height=1, picture="", valid="", error="", explicit_options=False):
        target = str(target).strip();
        if not target:
            raise SumXError("GET requires a variable or assignable target");
        try:
            value = self.evaluate(target);
        except Exception as exc:
            raise SumXError("GET target does not exist: {}".format(target)) from exc;
        if isinstance(value, (bytes, bytearray)):
            raise SumXError("GET does not edit BLOB/BYTE values directly");
        shown = display_value(value);
        fixed = isinstance(value, str) and not explicit_options and not picture;
        max_length = None;
        if picture:
            capacity = picture_capacity(picture);
            if self.runtime.field_wrap_overflow:
                max_length = None;
            elif capacity > 0:
                max_length = picture_display_width(picture);
            elif isinstance(value, str):
                max_length = max(1, len(value));
            shown = transform(value, picture, overflow=self.runtime.field_wrap_overflow);
        elif fixed:
            max_length = max(1, len(value));
        if width is None:
            if picture:
                width = picture_display_width(picture);
            elif isinstance(value, str):
                width = max(1, len(value));
            elif isinstance(value, bool):
                width = max(1, len(str(shown)));
            else:
                width = max(10, len(str(shown)));
        field = GetField(
            target, row, column, max(1, int(width)), str(shown), original=value, fixed=fixed,
            height=max(1, int(height)), picture=str(picture or ""), max_length=max_length,
            overflow=bool(self.runtime.field_wrap_overflow), window=self.runtime.active_window,
            valid=str(valid or ""), error=str(error or ""),
        );
        self.pending_gets.append(field);
        return field;

    @staticmethod
    def _numeric_picture_text(text):
        raw = str(text).strip();
        negative = raw.startswith("(") and raw.endswith(")");
        raw = raw.strip("()").replace("$", "").replace("*", "").replace(" ", "");
        raw = re.sub(r"(?i)(CR|DB)$", "", raw).strip();
        if "," in raw and "." in raw:
            raw = raw.replace(",", "");
        elif raw.count(",") == 1 and "." not in raw:
            raw = raw.replace(",", ".");
        if negative and not raw.startswith("-"):
            raw = "-" + raw;
        return raw;

    def _coerce_read_value(self, field, text):
        text = str(text);
        original = field.original;
        if field.picture:
            spec = parse_picture(field.picture);
            if isinstance(original, str):
                value = strip_picture_literals(text, spec) if spec.remove_literals else text;
                if spec.choices:
                    match = next((choice for choice in spec.choices if choice.casefold() == value.strip().casefold()), None);
                    if match is not None:
                        value = match;
                if spec.uppercase:
                    value = value.upper();
                if field.max_length is not None and not field.overflow:
                    value = value[:field.max_length];
                return value;
            if isinstance(original, bool):
                key = strip_picture_literals(text, spec).strip().upper();
                if key in ("T", "TRUE", ".T.", "Y", "YES", "S", "SI", "ON", "1", "V"):
                    return True;
                if key in ("F", "FALSE", ".F.", "N", "NO", "OFF", "0"):
                    return False;
                raise SumXError("Invalid logical value for {}: {}".format(field.target, text));
            if isinstance(original, int) and not isinstance(original, bool):
                return int(Decimal(self._numeric_picture_text(text)));
            if isinstance(original, float):
                return float(self._numeric_picture_text(text));
            if isinstance(original, Decimal):
                return Decimal(self._numeric_picture_text(text));
            return strip_picture_literals(text, spec) if spec.remove_literals else text;
        if isinstance(original, str):
            if field.fixed:
                limit = field.max_length if field.max_length is not None else field.width;
                return text[:limit].ljust(limit);
            return text.rstrip() if field.height <= 1 else text;
        if isinstance(original, bool):
            key = text.strip().upper();
            if key in ("T", "TRUE", ".T.", "Y", "YES", "ON", "1"):
                return True;
            if key in ("F", "FALSE", ".F.", "N", "NO", "OFF", "0"):
                return False;
            raise SumXError("Invalid logical value for {}: {}".format(field.target, text));
        if isinstance(original, int) and not isinstance(original, bool):
            return int(text.strip());
        if isinstance(original, float):
            return float(text.strip());
        if isinstance(original, Decimal):
            return Decimal(text.strip());
        if original is None:
            return text.rstrip();
        return text.rstrip();

    def validate_get_field(self, field, text):
        try:
            candidate = self._coerce_read_value(field, text);
        except Exception as exc:
            return False, field.error or str(exc);
        choices = picture_choices(field.picture) if field.picture else ();
        if choices:
            probe = str(candidate).strip().casefold();
            if probe not in tuple(choice.casefold() for choice in choices):
                return False, field.error or "Expected one of: {}".format(", ".join(choices));
        if not str(field.valid or "").strip():
            return True, "";
        try:
            previous = self.evaluate(field.target);
            self._assign_target(field.target, candidate);
            try:
                valid = bool(self.evaluate(field.valid));
            finally:
                self._assign_target(field.target, previous);
        except Exception as exc:
            return False, field.error or "VALID error: {}".format(exc);
        return valid, ("" if valid else str(field.error or ""));

    def apply_read_values(self, fields, values):
        for field in fields:
            text = str(values.get(field.target, field.value));
            valid, message = self.validate_get_field(field, text);
            if not valid:
                raise SumXError(message or "Validation failed for {}".format(field.target));
            self._assign_target(field.target, self._coerce_read_value(field, text));
        return True;

    def apply_input_value(self, request, entered):
        text = str(entered);
        original = None;
        if self.runtime.has_value(request.target):
            original = self.runtime.get_value(request.target);
        if text == "" and request.default_character:
            text = str(request.default_character);
        if request.text_only:
            value = text;
        elif request.keys:
            if not text:
                raise SumXError("INPUT requires one of: {}".format(request.keys));
            char = text[0];
            valid = request.keys if request.case_sensitive else request.keys.upper();
            probe = char if request.case_sensitive else char.upper();
            if probe not in valid:
                raise SumXError("INPUT expects one of: {}".format(request.keys));
            value = char;
        elif isinstance(original, bool):
            key = text.strip().upper();
            if key in ("T", "TRUE", ".T.", "Y", "YES", "ON", "1", "S", "SI"):
                value = True;
            elif key in ("F", "FALSE", ".F.", "N", "NO", "OFF", "0"):
                value = False;
            else:
                raise SumXError("Invalid logical value for {}: {}".format(request.target, text));
        elif isinstance(original, int) and not isinstance(original, bool):
            value = int(self._numeric_picture_text(text) if request.picture else text.strip());
        elif isinstance(original, float):
            value = float(self._numeric_picture_text(text) if request.picture else text.strip());
        elif isinstance(original, Decimal):
            value = Decimal(self._numeric_picture_text(text) if request.picture else text.strip());
        else:
            if request.picture:
                spec = parse_picture(request.picture);
                value = strip_picture_literals(text, spec) if spec.remove_literals else transform(text, spec, overflow=self.runtime.field_wrap_overflow).rstrip();
            else:
                value = text;
        self._assign_target(request.target, value);
        return value;

    @staticmethod
    def _input_option_start(body):
        names = ("HIDDEN", "MASK", "DIALOG", "WIDTH", "HEIGHT", "PICTURE", "KEYS", "CASE_SENSITIVE", "CASE-SENSITIVE", "DEFAULT", "TIMEOUT");
        quoted = None;
        escaped = False;
        candidates = [];
        index = 0;
        while index < len(body):
            char = body[index];
            if quoted is not None:
                if escaped:
                    escaped = False;
                elif char == "\\":
                    escaped = True;
                elif char == quoted:
                    quoted = None;
                index += 1;
                continue;
            if char in ("\"", "'"):
                quoted = char;
                index += 1;
                continue;
            if char.isalpha() or char == "_":
                end = index + 1;
                while end < len(body) and (body[end].isalnum() or body[end] in "_-"):
                    end += 1;
                word = body[index:end].upper();
                if word in names:
                    candidates.append(index);
                index = end;
                continue;
            index += 1;
        for position in candidates:
            core = body[:position].strip();
            parts = core.rsplit(None, 1);
            if len(parts) == 2 and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", parts[1]):
                return position;
        return None;

    @staticmethod
    def _input_option_tokens(source):
        return re.findall(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[^\s]+', str(source));

    def _input_option_value(self, token):
        try:
            return self.evaluate(token);
        except Exception:
            return str(token).strip().strip("\"").strip("'");

    def _parse_input_request(self, text):
        body = re.sub(r"(?is)^INPUT\s+", "", str(text), count=1).strip();
        if not body:
            raise SumXError("INPUT requires a prompt and target variable");
        option_start = self._input_option_start(body);
        option_source = "" if option_start is None else body[option_start:].strip();
        core = body if option_start is None else body[:option_start].strip();
        parts = core.rsplit(None, 1);
        if len(parts) != 2:
            raise SumXError('INPUT syntax: INPUT "Prompt" variable [options]');
        prompt_expression, target = parts;
        if prompt_expression.upper().endswith(" TO"):
            prompt_expression = prompt_expression[:-3].rstrip();
        if prompt_expression.endswith(","):
            prompt_expression = prompt_expression[:-1].rstrip();
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", target):
            raise SumXError("INPUT target must be a variable name");
        prompt = self.evaluate(prompt_expression);
        request = InputRequest(str(prompt), target);
        tokens = self._input_option_tokens(option_source);
        index = 0;
        while index < len(tokens):
            option = tokens[index].upper();
            if option == "HIDDEN":
                request.hidden = True;
                index += 1;
                continue;
            if option == "DIALOG":
                request.dialog = True;
                index += 1;
                continue;
            if option in ("CASE_SENSITIVE", "CASE-SENSITIVE"):
                request.case_sensitive = True;
                index += 1;
                continue;
            if option in ("MASK", "PICTURE", "KEYS", "DEFAULT", "WIDTH", "HEIGHT", "TIMEOUT"):
                if index + 1 >= len(tokens):
                    raise SumXError("INPUT {} requires a value".format(option));
                raw = tokens[index + 1];
                value = self._input_option_value(raw);
                if option == "MASK":
                    request.mask = str(value);
                elif option == "PICTURE":
                    request.picture = str(value);
                elif option == "KEYS":
                    request.keys = str(value);
                elif option == "DEFAULT":
                    request.default_character = str(value);
                elif option == "WIDTH":
                    request.width = max(1, int(value));
                elif option == "HEIGHT":
                    request.height = max(1, int(value));
                elif option == "TIMEOUT":
                    request.timeout_seconds = max(0.0, float(value));
                index += 2;
                continue;
            raise SumXError("Unknown INPUT option: {}".format(tokens[index]));
        if request.keys and request.default_character:
            valid = request.keys if request.case_sensitive else request.keys.upper();
            probe = request.default_character[0] if request.case_sensitive else request.default_character[0].upper();
            if probe not in valid:
                raise SumXError("INPUT DEFAULT must be one of KEYS: {}".format(request.keys));
        if request.height > 1 and (request.hidden or request.mask is not None or request.keys or request.picture):
            raise SumXError("INPUT HEIGHT > 1 currently cannot be combined with HIDDEN, MASK, KEYS or PICTURE");
        return request;

    def _parse_accept_request(self, text):
        body = re.sub(r"(?is)^ACCEPT\s*", "", str(text), count=1).strip();
        match = re.match(r"(?is)^(.*?)\s+TO\s+([A-Za-z_][A-Za-z0-9_]*)$", body);
        if not match:
            raise SumXError('ACCEPT syntax: ACCEPT "Prompt" TO variable');
        prompt_expression = match.group(1).strip();
        target = match.group(2);
        prompt = "" if not prompt_expression else self.evaluate(prompt_expression);
        return InputRequest(str(prompt), target, command="ACCEPT", text_only=True, dialog=False);

    def _parse_window_definition(self, text):
        match = re.match(
            r"(?is)^DEFINE\s+WINDOW\s+([A-Za-z_][A-Za-z0-9_]*)\s+FROM\s+(.+?)\s*,\s*(.+?)\s+TO\s+(.+?)\s*,\s*(.+?)(?=\s+(?:TITLE|SHADOW|PANEL|COLOR\s+SCHEME)\b|$)(.*)$",
            str(text).strip(),
        );
        if not match:
            raise SumXError("DEFINE WINDOW syntax: DEFINE WINDOW name FROM row,col TO row,col [TITLE text] [SHADOW] [PANEL] [COLOR SCHEME n]");
        name = match.group(1);
        top = self._coord(self.evaluate(match.group(2)), "WINDOW top");
        left = self._coord(self.evaluate(match.group(3)), "WINDOW left");
        bottom = self._coord(self.evaluate(match.group(4)), "WINDOW bottom");
        right = self._coord(self.evaluate(match.group(5)), "WINDOW right");
        if bottom < top or right < left:
            raise SumXError("DEFINE WINDOW TO coordinates must not precede FROM coordinates");
        tail = (match.group(6) or "").strip();
        title = name;
        title_match = re.search(r"(?is)\bTITLE\s+(.+?)(?=\s+(?:SHADOW|PANEL|COLOR\s+SCHEME)\b|$)", tail);
        if title_match:
            title = str(self.evaluate(title_match.group(1).strip()));
        color_scheme = None;
        color_match = re.search(r"(?is)\bCOLOR\s+SCHEME\s+(.+?)(?=\s+(?:TITLE|SHADOW|PANEL)\b|$)", tail);
        if color_match:
            color_scheme = int(self.evaluate(color_match.group(1).strip()));
        return {
            "name": name,
            "top": top,
            "left": left,
            "bottom": bottom,
            "right": right,
            "width": right - left + 1,
            "height": bottom - top + 1,
            "title": title,
            "shadow": bool(re.search(r"(?is)\bSHADOW\b", tail)),
            "panel": bool(re.search(r"(?is)\bPANEL\b", tail)),
            "color_scheme": color_scheme,
        };

    def _execute_one(self, text, interactive=True):
        text = str(text).strip();
        if not text:
            return None;
        upper = text.upper();
        if upper in ("QUIT", "EXIT"):
            return QuitResult();
        return_match = re.match(r"(?is)^RETURN(?:\s+(.+))?$", text);
        if return_match is not None:
            expression = (return_match.group(1) or "").strip();
            return ReturnResult(self.evaluate(expression) if expression else None);
        eval_match = re.match(r"(?is)^=\s*(.+)$", text);
        if eval_match is not None:
            self.evaluate(eval_match.group(1));
            return None;
        match = re.match(r"(?is)^HELP(?:\s+(.+))?$", text);
        if match:
            topic_name = (match.group(1) or "").strip();
            if topic_name:
                topic = find_topic(topic_name);
                if topic is None:
                    raise SumXError("Unknown help topic: {}".format(topic_name));
                help_text = topic.markdown();
                title = "sumX Help - {}".format(topic.name);
            else:
                help_text = index_markdown();
                title = "sumX Help";
            return HelpRequest(help_text, title=title) if interactive else self._output(help_text);
        if upper == "CLEAR":
            self.pending_gets = [];
            return ClearResult();
        match = re.match(r"(?is)^CURSOR\s+(.+)$", text);
        if match:
            raw = match.group(1).strip(); key = raw.upper();
            aliases = {
                "OFF": False, "HIDE": False, "FALSE": False, ".F.": False,
                "ON": True, "SHOW": True, "NORMAL": True, "UNDERSCORE": True, "UNDERLINE": True, "TRUE": True, ".T.": True,
                "BLOCK": "block",
            };
            value = aliases[key] if key in aliases else self.evaluate(raw);
            self.runtime.cursor(value);
            return None;

        if re.match(r"(?is)^INPUT(?:\s|$)", text):
            return self._parse_input_request(text);
        if re.match(r"(?is)^ACCEPT(?:\s|$)", text):
            return self._parse_accept_request(text);

        if re.match(r"(?is)^DEFINE\s+WINDOW\b", text):
            definition = self._parse_window_definition(text);
            stored = self.runtime.define_window(definition["name"], definition);
            return self._message("WINDOW {} defined {}x{} at {},{}".format(stored["name"], stored["width"], stored["height"], stored["top"], stored["left"]));
        match = re.match(r"(?is)^(?:ACTIVATE|SHOW)\s+WINDOW\s+([A-Za-z_][A-Za-z0-9_]*)$", text);
        if match:
            definition = self.runtime.activate_window(match.group(1));
            return WindowRequest("activate", definition["name"], definition);
        match = re.match(r"(?is)^(?:DEACTIVATE|HIDE)\s+WINDOW(?:\s+([A-Za-z_][A-Za-z0-9_]*))?$", text);
        if match:
            name = match.group(1) or self.runtime.active_window;
            if not name:
                raise SumXError("No active window");
            definition = self.runtime.get_window(name);
            self.runtime.deactivate_window(name);
            return WindowRequest("deactivate", definition["name"], definition);
        match = re.match(r"(?is)^RELEASE\s+WINDOW\s+([A-Za-z_][A-Za-z0-9_]*)$", text);
        if match:
            definition = self.runtime.release_window(match.group(1));
            return WindowRequest("release", definition["name"], definition);

        match = re.match(r"(?is)^@\s*(.+?)\s*,\s*(.+?)\s+(SAY|PRINT)\s+(.+)$", text);
        if match:
            row = self._coord(self.evaluate(match.group(1)), "@ {} row".format(match.group(3).upper()));
            column = self._coord(self.evaluate(match.group(2)), "@ {} column".format(match.group(3).upper()));
            say_expression, get_clause = self._split_get_clause(match.group(4));
            if get_clause is None:
                expression, picture_expression = self._split_picture_clause(say_expression);
                shown = self._format_expression(expression, picture_expression);
                return ScreenWriteResult(row, column, shown, window=self.runtime.active_window);
            shown = display_value(self.evaluate(say_expression));
            target, field_width, field_height, picture, valid, error, explicit = self._parse_get_clause(get_clause);
            field = self._make_get_field(
                target, row, column + len(shown) + 1, width=field_width, height=field_height,
                picture=picture, valid=valid, error=error, explicit_options=explicit,
            );
            return BatchResult([ScreenWriteResult(row, column, shown, window=self.runtime.active_window), ScreenGetResult(field)]);

        match = re.match(r"(?is)^@\s*(.+?)\s*,\s*(.+?)\s+GET\s+(.+)$", text);
        if match:
            row = self._coord(self.evaluate(match.group(1)), "@ GET row");
            column = self._coord(self.evaluate(match.group(2)), "@ GET column");
            target, field_width, field_height, picture, valid, error, explicit = self._parse_get_clause(match.group(3));
            return ScreenGetResult(self._make_get_field(target, row, column, width=field_width, height=field_height, picture=picture, valid=valid, error=error, explicit_options=explicit));

        if upper == "READ":
            fields = self.pending_gets;
            self.pending_gets = [];
            if not fields:
                return self._message("READ: no pending GET fields");
            return ReadRequest(fields);

        if text.startswith("??"):
            expression, picture_expression = self._split_picture_clause(text[2:].strip());
            return self._output(self._format_expression(expression, picture_expression));
        if text.startswith("?"):
            expression, picture_expression = self._split_picture_clause(text[1:].strip());
            return self._output(self._format_expression(expression, picture_expression));
        match = re.match(r"(?is)^(?:PRINT|SAY)(?:\s+(.*))?$", text);
        if match:
            body = (match.group(1) or '""').strip();
            expression, picture_expression = self._split_picture_clause(body);
            return self._output(self._format_expression(expression, picture_expression));

        match = re.match(r"(?is)^SET\s+(?:DEBUG_LEVEL|DEBUG)\s+([A-Za-z0-9_.]+)$", text);
        if match:
            try:
                level = self.runtime.set_debug_level(match.group(1));
            except ValueError as exc:
                raise SumXError(str(exc)) from exc;
            return self._message("DEBUG_LEVEL {}".format(level), level="INFO");

        match = re.match(r"(?is)^SET\s+TALK\s+(.+)$", text);
        if match:
            value = self.evaluate(match.group(1));
            if not isinstance(value, bool):
                raise SumXError("TALK expects ON/OFF or TRUE/FALSE");
            level = self.runtime.set_debug_level("INFO" if value else "OFF");
            return self._message("TALK {} (DEBUG_LEVEL {})".format("ON" if value else "OFF", level), level="INFO");

        match = re.match(r"(?is)^SET\s+CAPS_SENSITIVE\s+(.+)$", text);
        if match:
            value = self.evaluate(match.group(1));
            if not isinstance(value, bool):
                raise SumXError("CAPS_SENSITIVE expects ON/OFF or TRUE/FALSE");
            self.runtime.set_caps_sensitive(value);
            return self._message("CAPS_SENSITIVE {}".format("ON" if value else "OFF"));

        match = re.match(r"(?is)^SET\s+FIELD_WRAP_OVERFLOW\s+(.+)$", text);
        if match:
            value = self.evaluate(match.group(1));
            if not isinstance(value, bool):
                raise SumXError("FIELD_WRAP_OVERFLOW expects ON/OFF or TRUE/FALSE");
            self.runtime.set_field_wrap_overflow(value);
            return self._message("FIELD_WRAP_OVERFLOW {}".format("ON" if value else "OFF"));

        match = re.match(r"(?is)^SET\s+CONFIRM\s+(.+)$", text);
        if match:
            value = self.evaluate(match.group(1));
            if not isinstance(value, bool):
                raise SumXError("CONFIRM expects ON/OFF or TRUE/FALSE");
            self.runtime.set_confirm(value);
            return self._message("CONFIRM {}".format("ON" if value else "OFF"));

        match = re.match(r"(?is)^SET\s+LINE_CONTINUATION\s+(?:TO\s+)?(BACKSLASH|SEMICOLON)$", text);
        if match:
            mode = self.runtime.set_line_continuation(match.group(1));
            return self._message("LINE_CONTINUATION {}".format(mode));

        match = re.match(r"(?is)^SET\s+AMPERSAND_COMMENT\s+(.+)$", text);
        if match:
            value = self.evaluate(match.group(1));
            if not isinstance(value, bool):
                raise SumXError("AMPERSAND_COMMENT expects ON/OFF or TRUE/FALSE");
            self.runtime.set_ampersand_comment(value);
            return self._message("AMPERSAND_COMMENT {}".format("ON" if value else "OFF"));

        match = re.match(r"(?is)^STORE\s+(.+?)\s+TO\s+([A-Za-z_][A-Za-z0-9_]*)$", text);
        if match:
            value = self.evaluate(match.group(1));
            self.runtime.set_value(match.group(2), value);
            return self._message("{} = {}".format(match.group(2), display_value(value)));
        match = re.match(r"(?is)^LET\s+(.+?)\s*=\s*(.+)$", text);
        if match:
            value = self._execute_sql_value(match.group(2)) if parse_sql_source(match.group(2), runtime=self.runtime) else self.evaluate(match.group(2));
            self._assign_target(match.group(1), value);
            return self._message("{} = {}".format(match.group(1).strip(), display_value(value)));

        match = re.match(r"(?is)^CREATE\s+(?:DATABASE|DB)\s+(.+)$", text);
        if match:
            path = match.group(1).strip().strip('"').strip("'");
            self.runtime.db.open(path);
            return self._message("Database created/opened: {}".format(path));
        match = re.match(r"(?is)^OPEN\s+(?:DATABASE|DB)\s+(.+)$", text);
        if match:
            path = match.group(1).strip().strip('"').strip("'");
            self.runtime.db.open(path);
            return self._message("Database opened: {}".format(path));
        match = re.match(r"(?is)^CREATE\s+TABLE\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((.*)\)\s*$", text);
        if match:
            name = match.group(1);
            defs = split_top_level(match.group(2));
            columns = self.runtime.db.create_table(name, defs);
            return self._message("Table {} created ({} columns)".format(name, len(columns)));
        match = re.match(r"(?is)^CREATE\s+(UNIQUE\s+)?INDEX\s+([A-Za-z_][A-Za-z0-9_]*)\s+ON\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((.*)\)\s*$", text);
        if match:
            self.runtime.db.create_index(match.group(2), match.group(3), match.group(4), unique=bool(match.group(1)));
            return self._message("Index {} created".format(match.group(2)));
        match = re.match(r"(?is)^CREATE\s+(OR\s+REPLACE\s+)?VIEW\s+([A-Za-z_][A-Za-z0-9_]*)\s+AS\s+(.+)$", text);
        if match:
            body = match.group(3).strip();
            parsed = parse_sql_source(body, runtime=self.runtime);
            if parsed:
                _mode, sql_text = parsed;
            else:
                sql_text = body;
            name = self.runtime.db.create_view(match.group(2), sql_text, replace=bool(match.group(1)));
            return self._message("View {} created".format(name));
        match = re.match(r"(?is)^LINK(?:\s+TABLES?)?\s+([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\s+TO\s+([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)(?:\s+AS\s+([A-Za-z_][A-Za-z0-9_]*))?$", text);
        if match:
            name = match.group(5) or "{}_{}_to_{}_{}".format(match.group(1), match.group(2), match.group(3), match.group(4));
            self.runtime.db.create_relation(name, match.group(1), match.group(2), match.group(3), match.group(4));
            return self._message("Relation {} created".format(name));
        match = re.match(r"(?is)^CREATE\s+RELATION\s+([A-Za-z_][A-Za-z0-9_]*)\s+FROM\s+([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\s+TO\s+([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)$", text);
        if match:
            self.runtime.db.create_relation(match.group(1), match.group(2), match.group(3), match.group(4), match.group(5));
            return self._message("Relation {} created".format(match.group(1)));
        match = re.match(r"(?is)^CREATE\s+FORM\s+([A-Za-z_][A-Za-z0-9_]*)\s+(?:FROM|FOR)\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s+TITLE\s+(.+))?$", text);
        if match:
            title = match.group(3);
            if title:
                title = title.strip().strip('"').strip("'");
            definition = self.runtime.db.create_form(match.group(1), match.group(2), title=title);
            return self._message("Form {} created for {}".format(definition["name"], definition["table"]));
        match = re.match(r"(?is)^(?:DO\s+)?FORM\s+([A-Za-z_][A-Za-z0-9_]*)$", text);
        if match:
            form = self.runtime.db.get_form(match.group(1));
            return FormRequest(form["name"], form["table"], self.runtime.db.columns(form["table"]), form["title"]);

        match = re.match(r"(?is)^DO\s+(.+)$", text);
        if match:
            target = match.group(1).strip();
            if re.match(r"(?is)^(?:CASE|WHILE)\b", target):
                raise SumXError("{} control flow is not implemented yet".format("DO " + target.split(None, 1)[0].upper()));
            path = self._resolve_program_path(target);
            results = self.run_file(path, interactive=interactive);
            if not results:
                return None;
            return BatchResult(results) if len(results) > 1 else results[0];

        match = re.match(r"(?is)^USE(?:\s+([A-Za-z_][A-Za-z0-9_]*))?(?:\s+(?:ALIAS|AS)\s+([A-Za-z_][A-Za-z0-9_]*))?$", text);
        if match:
            area = self.runtime.db.use(match.group(1), alias=match.group(2));
            if area.table:
                alias = " AS {}".format(area.alias) if area.alias and area.alias.casefold() != area.table.casefold() else "";
                return self._message("Channel {}/{}: {}{}".format(area.letter, area.number, area.table, alias));
            return self._message("Channel {}/{}: closed".format(area.letter, area.number));
        match = re.match(r"(?is)^(?:CHANNEL|CHAN|SELECT|SEL|SELE)\s+([A-Za-z_][A-Za-z0-9_]*|\d+)$", text);
        if match:
            number = self.runtime.db.select(match.group(1));
            area = self.runtime.db.current_area;
            detail = area.alias or area.table or "empty";
            return self._message("Channel {}/{} selected: {}".format(area.letter, number, detail));

        if re.match(r"(?is)^(?:DISPLAY|DISP)\s+WORKAREAS$", text):
            return TableResult("Work areas", ["Area", "Alias", "Table", "Rec", "Count", "Relation"], self.runtime.db.workareas_rows());
        if re.match(r"(?is)^(?:DISPLAY|DISP)\s+(?:STRUCTURE|STRU)$", text):
            cols = self.runtime.db.columns();
            rows = [[col.name, col.declared_type, str(col.length or ""), str(col.precision or ""), str(col.scale or ""), "Y" if col.nullable else "N", "Y" if col.autoinum else ""] for col in cols];
            return TableResult("Structure: {}".format(self.runtime.db.current_area.table), ["Name", "Type", "Len", "Prec", "Scale", "Null", "Auto"], rows);
        if upper in ("TABLES", "DISPLAY TABLES", "DISP TABLES"):
            return TableResult("Tables", ["Name"], [[name] for name in self.runtime.db.list_tables()]);
        if upper in ("VIEWS", "DISPLAY VIEWS", "DISP VIEWS"):
            return TableResult("Views", ["Name", "SQL"], [[name, sql] for name, sql in self.runtime.db.list_views()]);
        if upper in ("RELATIONS", "DISPLAY RELATIONS", "DISP RELATIONS"):
            return TableResult("Relations", ["Name", "From table", "From field", "To table", "To field"], self.runtime.db.relation_rows());

        match = re.match(r"(?is)^APPEND(?:\s+(.*))?$", text);
        if match:
            tail = (match.group(1) or "").strip();
            table = self.runtime.db._require_table();
            if not tail:
                return AppendRequest(table, self.runtime.db.columns(table), title="Append: {}".format(table));
            if tail.upper() == "BLANK":
                rowid = self.runtime.db.append({}, table=table);
                return self._message("Blank record appended (rowid {})".format(rowid));
            values = {};
            for item in split_top_level(tail):
                pair = re.match(r"(?is)^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$", item);
                if not pair:
                    raise SumXError("APPEND expects field=expression pairs");
                values[pair.group(1)] = self.evaluate(pair.group(2));
            rowid = self.runtime.db.append(values, table=table);
            return self._message("Record appended (rowid {})".format(rowid));

        match = re.match(r"(?is)^(?:BROWSE|BROW|BROWS)(?:\s+(.+?))?(?:\s+LIMIT\s+(\d+))?$", text);
        if match:
            expression = (match.group(1) or "").strip();
            limit = int(match.group(2) or 200);
            if expression:
                value = self._execute_sql_value(expression) if parse_sql_source(expression, runtime=self.runtime) else self.evaluate(expression);
                columns, rows = tabularize(value);
                return BrowseRequest("Browse: {}".format(expression), columns, rows[:limit], table=None, readonly=True);
            table = self.runtime.db._require_table();
            columns, rows = self.runtime.db.browse(limit=limit);
            return BrowseRequest("Browse: {}".format(table), columns, rows, table=table, readonly=self.runtime.db.is_view(table));
        match = re.match(r"(?is)^LIST(?:\s+(.+?))?(?:\s+LIMIT\s+(\d+))?$", text);
        if match:
            expression = (match.group(1) or "").strip();
            limit = int(match.group(2) or 200);
            if expression:
                value = self.evaluate(expression);
                columns, rows = tabularize(value);
                return TableResult("List: {}".format(expression), columns, rows[:limit]);
            table = self.runtime.db._require_table();
            columns, rows = self.runtime.db.browse(limit=limit);
            return TableResult("List: {}".format(table), columns, rows);

        match = re.match(r"(?is)^GO(?:TO)?\s+(TOP|BOTTOM|\d+)$", text);
        if match:
            number = self.runtime.db.go(match.group(1));
            return self._message("Record {}".format(number));
        match = re.match(r"(?is)^SKIP(?:\s+(-?\d+))?$", text);
        if match:
            number = self.runtime.db.skip(int(match.group(1) or 1));
            return self._message("Record {}".format(number));
        match = re.match(r"(?is)^SET\s+RELATION\s+TO\s+([A-Za-z_][A-Za-z0-9_]*)\s+INTO\s+([A-Za-z_][A-Za-z0-9_]*|\d+)(?:\s+ON\s+([A-Za-z_][A-Za-z0-9_]*))?$", text);
        if match:
            source_number = self.runtime.db.active_area;
            self.runtime.db.select(match.group(2));
            target_area = self.runtime.db.current_area;
            self.runtime.db.select(str(source_number));
            source = self.runtime.db.current_area;
            source.relation = "{}.{}→{}.{}".format(source.alias or source.table, match.group(1), target_area.alias or target_area.table, match.group(3) or match.group(1));
            return self._message("Relation: {}".format(source.relation));

        if parse_sql_source(text, runtime=self.runtime):
            value = self._execute_sql_value(text);
            return self._result_for_value(value, title="SQL");

        match = re.match(r"(?is)^(.+?)\s*=\s*(.+)$", text);
        if match:
            left = match.group(1).strip();
            right = match.group(2).strip();
            value = self._execute_sql_value(right) if parse_sql_source(right, runtime=self.runtime) else self.evaluate(right);
            self._assign_target(left, value);
            return self._message("{} = {}".format(left, display_value(value)));
        try:
            node = self.expr.parse(text);
            if isinstance(node, ast.Call):
                value = self.expr._eval(node);
                return None if value is None else self._result_for_value(value);
        except Exception:
            pass;
        raise SumXError("Unknown command: {}".format(text));

    def run_file(self, path, interactive=False):
        path = self._resolve_program_path(path) if not isinstance(path, Path) or not path.is_file() else path.resolve();
        source = path.read_text(encoding="utf-8", errors="replace");
        self.source_stack.append(path);
        try:
            results = self.execute_many(source, interactive=interactive);
        finally:
            self.source_stack.pop();
        return [result for result in results if not isinstance(result, ReturnResult)];
