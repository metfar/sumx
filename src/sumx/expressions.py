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
import operator;
import re;
from datetime import date, datetime;
from decimal import Decimal;
from pathlib import Path;
from sumdata import read_rds, save_rds;

from .picture import transform;
from .values import SumCursor, SumObject, SumQuery, SumRow;


class ExpressionError(ValueError):
    pass;


def _outside_strings(text, transform):
    source = str(text);
    out = [];
    chunk = [];
    index = 0;
    while index < len(source):
        if source.startswith('"""', index) or source.startswith("'''", index):
            if chunk:
                out.append(transform("".join(chunk)));
                chunk = [];
            quote = source[index:index + 3];
            end = index + 3;
            escaped = False;
            while end < len(source):
                if not escaped and source.startswith(quote, end):
                    end += 3;
                    break;
                char = source[end];
                if escaped:
                    escaped = False;
                elif char == "\\":
                    escaped = True;
                end += 1;
            out.append(source[index:end]);
            index = end;
            continue;
        char = source[index];
        if char in ("'", '"'):
            if chunk:
                out.append(transform("".join(chunk)));
                chunk = [];
            quote = char;
            end = index + 1;
            escaped = False;
            while end < len(source):
                current = source[end];
                if escaped:
                    escaped = False;
                elif current == "\\":
                    escaped = True;
                elif current == quote:
                    end += 1;
                    break;
                end += 1;
            out.append(source[index:end]);
            index = end;
            continue;
        chunk.append(char);
        index += 1;
    if chunk:
        out.append(transform("".join(chunk)));
    return "".join(out);


def normalize_expression(source, equality=False, ampersand_comment=False):
    def rewrite(text):
        text = re.sub(r"(?i)\.T\.|\bTRUE\b|\bON\b", "True", text);
        text = re.sub(r"(?i)\.F\.|\bFALSE\b|\bOFF\b", "False", text);
        text = re.sub(r"(?i)\.NULL\.|\bNULL\b|\bNONE\b|\bNIL\b", "None", text);
        text = re.sub(r"(?i)\.AND\.|\bAND\b", " and ", text);
        text = re.sub(r"(?i)\.XOR\.|\bXOR\b", " ^ ", text);
        text = re.sub(r"(?i)\.OR\.|\bOR\b", " or ", text);
        text = re.sub(r"(?i)\.NOT\.|\bNOT\b", " not ", text);
        if not ampersand_comment:
            text = text.replace("&&", " and ");
        text = text.replace("||", " or ");
        text = text.replace("^^", " ^ ");
        text = text.replace("¬", " not ");
        text = re.sub(r"(?<![<>=!])~", " not ", text);
        text = re.sub(r"(?i)\bIN\b", " in ", text);
        text = re.sub(r"(?i)\bIS\b", " is ", text);
        text = text.replace("$", " in ");
        text = text.replace("<>", "!=");
        if equality:
            text = re.sub(r"(?<![<>=!])=(?!=)", "==", text);
        return text;
    return _outside_strings(str(source), rewrite).strip();


class ExpressionEvaluator:
    BINOPS = {
        ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.BitXor: lambda left, right: bool(left) ^ bool(right),
    };
    CMPOPS = {
        ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt, ast.LtE: operator.le,
        ast.Gt: operator.gt, ast.GtE: operator.ge, ast.In: lambda left, right: left in right,
        ast.NotIn: lambda left, right: left not in right, ast.Is: operator.is_, ast.IsNot: operator.is_not,
    };
    SAFE_METHODS = {
        "append", "extend", "insert", "pop", "remove", "clear", "sort", "reverse",
        "count", "index", "get", "keys", "values", "items", "copy", "execute",
    };

    def __init__(self, runtime):
        self.runtime = runtime;

    def parse(self, source):
        normalized = normalize_expression(source, equality=False, ampersand_comment=self.runtime.ampersand_comment);
        try:
            return ast.parse(normalized, mode="eval").body;
        except SyntaxError:
            normalized = normalize_expression(source, equality=True, ampersand_comment=self.runtime.ampersand_comment);
            try:
                return ast.parse(normalized, mode="eval").body;
            except SyntaxError as exc:
                raise ExpressionError("Invalid expression: {}".format(source)) from exc;

    def evaluate(self, source):
        return self._eval(self.parse(source));

    def _eval(self, node):
        if isinstance(node, ast.Constant):
            return node.value;
        if isinstance(node, ast.Name):
            return self.runtime.get_value(node.id);
        if isinstance(node, ast.List):
            return [self._eval(item) for item in node.elts];
        if isinstance(node, ast.Tuple):
            return tuple(self._eval(item) for item in node.elts);
        if isinstance(node, ast.Dict):
            return {self._eval(key): self._eval(value) for key, value in zip(node.keys, node.values)};
        if isinstance(node, ast.UnaryOp):
            value = self._eval(node.operand);
            if isinstance(node.op, ast.Not):
                return not value;
            if isinstance(node.op, ast.USub):
                return -value;
            if isinstance(node.op, ast.UAdd):
                return +value;
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                result = True;
                for item in node.values:
                    result = self._eval(item);
                    if not result:
                        return result;
                return result;
            if isinstance(node.op, ast.Or):
                result = False;
                for item in node.values:
                    result = self._eval(item);
                    if result:
                        return result;
                return result;
        if isinstance(node, ast.BinOp) and type(node.op) in self.BINOPS:
            return self.BINOPS[type(node.op)](self._eval(node.left), self._eval(node.right));
        if isinstance(node, ast.Compare):
            left = self._eval(node.left);
            for op_node, comparator in zip(node.ops, node.comparators):
                op = self.CMPOPS.get(type(op_node));
                if op is None:
                    raise ExpressionError("Unsupported comparison");
                right = self._eval(comparator);
                if not op(left, right):
                    return False;
                left = right;
            return True;
        if isinstance(node, ast.Subscript):
            value = self._eval(node.value);
            key = self._eval_slice(node.slice);
            return value[key];
        if isinstance(node, ast.Attribute):
            value = self._eval(node.value);
            if isinstance(value, (SumObject, SumRow)):
                return getattr(value, node.attr);
            raise ExpressionError("Attribute access is only available on OBJ/ROW values");
        if isinstance(node, ast.Call):
            args = [self._eval(item) for item in node.args];
            kwargs = {item.arg: self._eval(item.value) for item in node.keywords if item.arg is not None};
            if isinstance(node.func, ast.Name):
                return self._call(node.func.id, args, kwargs);
            if isinstance(node.func, ast.Attribute):
                target = self._eval(node.func.value);
                method = node.func.attr;
                if method not in self.SAFE_METHODS:
                    raise ExpressionError("Method not allowed: {}".format(method));
                func = getattr(target, method, None);
                if not callable(func):
                    raise ExpressionError("Unknown method: {}".format(method));
                return func(*args, **kwargs);
        raise ExpressionError("Unsupported expression element: {}".format(type(node).__name__));

    def _eval_slice(self, node):
        if isinstance(node, ast.Slice):
            lower = self._eval(node.lower) if node.lower is not None else None;
            upper = self._eval(node.upper) if node.upper is not None else None;
            step = self._eval(node.step) if node.step is not None else None;
            return slice(lower, upper, step);
        return self._eval(node);

    def _call(self, name, args, kwargs=None):
        kwargs = kwargs or {};
        key = str(name).upper();
        if key == "OBJ":
            return SumObject(*args, **kwargs);
        if key == "LIST":
            if kwargs:
                raise ExpressionError("LIST does not accept named arguments");
            return list(args[0]) if args else [];
        if key == "TUPLE":
            if kwargs:
                raise ExpressionError("TUPLE does not accept named arguments");
            return tuple(args[0]) if args else tuple();
        if key == "DICT":
            if kwargs:
                return dict(kwargs);
            return dict(args[0]) if args else {};
        if kwargs:
            raise ExpressionError("{} does not accept named arguments".format(name));
        funcs = {
            "LEN": lambda value: len(value),
            "SPACE": lambda count: " " * max(0, int(count)),
            "REPLICATE": lambda value, count: value * max(0, int(count)),
            "UPPER": lambda value: str(value).upper(),
            "LOWER": lambda value: str(value).lower(),
            "STR": lambda value: str(value),
            "VAL": lambda value: Decimal(str(value)),
            "DECIMAL": lambda value: Decimal(str(value)),
            "INT": lambda value: int(value),
            "FLOAT": lambda value: float(value),
            "ABS": abs,
            "ROUND": round,
            "DATE": lambda: date.today().isoformat(),
            "DATETIME": lambda: datetime.now().isoformat(timespec="seconds"),
            "RECNO": lambda: self.runtime.db.recno(),
            "RECCOUNT": lambda: self.runtime.db.reccount(),
            "ALIAS": lambda: self.runtime.db.current_area.alias or self.runtime.db.current_area.table or "",
            "SELECT": lambda: self.runtime.db.active_area,
            "CHANNEL": lambda: self.runtime.db.active_area,
            "BLOBFILE": lambda path: Path(str(path)).read_bytes(),
            "BYTEFILE": lambda path: Path(str(path)).read_bytes(),
            "TYPE": lambda value: type(value).__name__,
            "TRANSFORM": lambda value, picture: transform(value, picture, overflow=self.runtime.field_wrap_overflow),
            "WCOLS": lambda: self.runtime.screen_size()[0],
            "WROWS": lambda: self.runtime.screen_size()[1],
            "SCREENCOLS": lambda: self.runtime.screen_size()[0],
            "SCREENROWS": lambda: self.runtime.screen_size()[1],
            "MESSAGEBOX": lambda text, flags=0, title="Message": self.runtime.messagebox(text, flags, title),
            "READRDS": lambda path: read_rds(path),
            "SAVERDS": lambda path, value: save_rds(path, value),
        };
        if key not in funcs:
            handler = getattr(self.runtime, "_user_function_handler", None);
            if callable(handler):
                try:
                    return handler(name, args);
                except KeyError:
                    pass;
            raise ExpressionError("Unknown function {}".format(name));
        try:
            return funcs[key](*args);
        except TypeError as exc:
            raise ExpressionError("Bad arguments for {}".format(name)) from exc;
