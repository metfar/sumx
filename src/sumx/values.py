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
from collections.abc import MutableMapping, Sequence;
from dataclasses import dataclass;


class SumObject(MutableMapping):
    """Small dynamic object: mapping semantics plus attribute access."""

    def __init__(self, *args, **kwargs):
        object.__setattr__(self, "_data", {});
        if args:
            if len(args) > 1:
                raise TypeError("OBJ accepts at most one positional mapping");
            source = args[0];
            if isinstance(source, SumObject):
                source = source._data;
            self._data.update(dict(source));
        self._data.update(kwargs);

    def __getitem__(self, key):
        return self._data[key];

    def __setitem__(self, key, value):
        self._data[key] = value;

    def __delitem__(self, key):
        del self._data[key];

    def __iter__(self):
        return iter(self._data);

    def __len__(self):
        return len(self._data);

    def __getattr__(self, name):
        try:
            return self._data[name];
        except KeyError as exc:
            raise AttributeError(name) from exc;

    def __setattr__(self, name, value):
        if name.startswith("_"):
            object.__setattr__(self, name, value);
        else:
            self._data[name] = value;

    def __repr__(self):
        return "OBJ({})".format(", ".join("{}={!r}".format(key, value) for key, value in self._data.items()));

    def to_dict(self):
        return dict(self._data);


class SumRow(Sequence):
    """Immutable SQL row with positional, key, and attribute access."""

    def __init__(self, columns, values):
        self.columns = tuple(str(item) for item in columns);
        self.values = tuple(values);
        self._lookup = {name.casefold(): index for index, name in enumerate(self.columns)};

    def __len__(self):
        return len(self.values);

    def __iter__(self):
        return iter(self.values);

    def __getitem__(self, key):
        if isinstance(key, str):
            folded = key.casefold();
            if folded not in self._lookup:
                raise KeyError(key);
            return self.values[self._lookup[folded]];
        return self.values[key];

    def __getattr__(self, name):
        try:
            return self[name];
        except KeyError as exc:
            raise AttributeError(name) from exc;

    def __repr__(self):
        return "ROW({})".format(", ".join("{}={!r}".format(name, value) for name, value in zip(self.columns, self.values)));

    def to_dict(self):
        return dict(zip(self.columns, self.values));


class SumCursor(Sequence):
    """Materialized, reusable query result."""

    def __init__(self, columns, rows=None, name=None, sql=None):
        self.columns = tuple(str(item) for item in columns);
        self.name = str(name) if name else None;
        self.sql = str(sql) if sql else None;
        self.rows = [];
        for row in rows or []:
            self.rows.append(row if isinstance(row, SumRow) else SumRow(self.columns, row));

    def __len__(self):
        return len(self.rows);

    def __iter__(self):
        return iter(self.rows);

    def __getitem__(self, key):
        return self.rows[key];

    def __repr__(self):
        name = " {}".format(self.name) if self.name else "";
        return "<Cursor{}: {} rows x {} cols>".format(name, len(self.rows), len(self.columns));


@dataclass
class SqlExecResult:
    rowcount: int;
    lastrowid: object = None;

    def __repr__(self):
        return "<SQL: {} rows affected>".format(self.rowcount);


class SumQuery:
    """Reusable SQL query bound to a runtime."""

    def __init__(self, runtime, sql):
        self.runtime = runtime;
        self.sql = str(sql);

    def execute(self, **params):
        return self.runtime.execute_sql(self.sql, params=params);

    def __repr__(self):
        return "<Query {!r}>".format(self.sql.strip());


def display_value(value):
    if value is None:
        return "NULL";
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE";
    if isinstance(value, bytes):
        return "<{} bytes>".format(len(value));
    return str(value);


def tabularize(value):
    """Return (columns, rows) for generic BROWSE/LIST input."""
    if isinstance(value, SumCursor):
        return list(value.columns), [[display_value(item) for item in row] for row in value];
    if isinstance(value, SumRow):
        return list(value.columns), [[display_value(item) for item in value]];
    if isinstance(value, SumObject):
        return ["Field", "Value"], [[str(key), display_value(item)] for key, item in value.items()];
    if isinstance(value, dict):
        return ["Key", "Value"], [[display_value(key), display_value(item)] for key, item in value.items()];
    if isinstance(value, (list, tuple)):
        items = list(value);
        if not items:
            return ["Value"], [];
        if all(isinstance(item, SumRow) for item in items):
            columns = list(items[0].columns);
            return columns, [[display_value(cell) for cell in row] for row in items];
        if all(isinstance(item, SumObject) for item in items):
            keys = [];
            for item in items:
                for key in item.keys():
                    if key not in keys:
                        keys.append(key);
            return keys, [[display_value(item.get(key)) for key in keys] for item in items];
        if all(isinstance(item, dict) for item in items):
            keys = [];
            for item in items:
                for key in item.keys():
                    if key not in keys:
                        keys.append(key);
            return [str(key) for key in keys], [[display_value(item.get(key)) for key in keys] for item in items];
        if all(isinstance(item, (list, tuple)) for item in items):
            width = max(len(item) for item in items);
            columns = ["C{}".format(index + 1) for index in range(width)];
            return columns, [[display_value(item[index]) if index < len(item) else "" for index in range(width)] for item in items];
        return ["Value"], [[display_value(item)] for item in items];
    return ["Value"], [[display_value(value)]];
