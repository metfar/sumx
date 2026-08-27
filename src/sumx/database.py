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
import json;
import re;
import sqlite3;
from dataclasses import dataclass;
from pathlib import Path;

from .types import ColumnDef;


class DatabaseError(RuntimeError):
    pass;


def quote_ident(name):
    name = str(name);
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
        raise DatabaseError("Invalid identifier: {}".format(name));
    return '"{}"'.format(name);


def split_top_level(text, separator=","):
    items = [];
    chunk = [];
    level = 0;
    quote = None;
    for char in str(text):
        if quote is not None:
            chunk.append(char);
            if char == quote:
                quote = None;
            continue;
        if char in ("'", '"'):
            quote = char;
            chunk.append(char);
        elif char == "(":
            level += 1;
            chunk.append(char);
        elif char == ")":
            level = max(0, level - 1);
            chunk.append(char);
        elif char == separator and level == 0:
            items.append("".join(chunk).strip());
            chunk = [];
        else:
            chunk.append(char);
    if chunk or str(text).endswith(separator):
        items.append("".join(chunk).strip());
    return [item for item in items if item];


@dataclass
class WorkArea:
    number: int;
    table: str = None;
    alias: str = None;
    recno: int = 0;
    relation: str = None;

    @property
    def letter(self):
        return chr(ord("A") + self.number - 1) if 1 <= self.number <= 26 else str(self.number);


class SumXDatabase:
    def __init__(self, path=":memory:", max_areas=32):
        self.max_areas = max(10, int(max_areas));
        self.areas = {number: WorkArea(number) for number in range(1, self.max_areas + 1)};
        self.active_area = 1;
        self.path = None;
        self.connection = None;
        self.open(path);

    def open(self, path):
        if self.connection is not None:
            self.connection.close();
        self.path = str(path or ":memory:");
        self.connection = sqlite3.connect(self.path);
        self.connection.row_factory = sqlite3.Row;
        self.connection.execute("PRAGMA foreign_keys = ON");
        self._init_metadata();
        for area in self.areas.values():
            area.table = None;
            area.alias = None;
            area.recno = 0;
            area.relation = None;
        self.active_area = 1;
        return self;

    def close(self):
        if self.connection is not None:
            self.connection.close();
            self.connection = None;

    def _init_metadata(self):
        self.connection.executescript('''
CREATE TABLE IF NOT EXISTS __sumx_columns (
    table_name TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    name TEXT NOT NULL,
    logical_type TEXT NOT NULL,
    declared_type TEXT NOT NULL,
    sqlite_type TEXT NOT NULL,
    length INTEGER,
    precision_value INTEGER,
    scale_value INTEGER,
    nullable INTEGER NOT NULL,
    default_sql TEXT,
    primary_key INTEGER NOT NULL,
    unique_value INTEGER NOT NULL,
    autoinum INTEGER NOT NULL,
    references_table TEXT,
    references_column TEXT,
    PRIMARY KEY(table_name, name)
);
CREATE TABLE IF NOT EXISTS __sumx_forms (
    name TEXT PRIMARY KEY,
    table_name TEXT NOT NULL,
    title TEXT NOT NULL,
    definition_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS __sumx_relations (
    name TEXT PRIMARY KEY,
    source_table TEXT NOT NULL,
    source_column TEXT NOT NULL,
    target_table TEXT NOT NULL,
    target_column TEXT NOT NULL
);
''');
        self.connection.commit();

    @property
    def current_area(self):
        return self.areas[self.active_area];

    def table_exists(self, name):
        row = self.connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (str(name),)).fetchone();
        return row is not None;

    def view_exists(self, name):
        row = self.connection.execute("SELECT 1 FROM sqlite_master WHERE type='view' AND name=?", (str(name),)).fetchone();
        return row is not None;

    def source_exists(self, name):
        row = self.connection.execute("SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name=?", (str(name),)).fetchone();
        return row is not None;

    def is_view(self, name):
        return bool(name) and self.view_exists(name);

    def list_tables(self):
        rows = self.connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE '__sumx_%' ORDER BY name").fetchall();
        return [row[0] for row in rows];

    def list_views(self):
        rows = self.connection.execute("SELECT name, sql FROM sqlite_master WHERE type='view' ORDER BY name").fetchall();
        return [(row[0], row[1] or "") for row in rows];

    def select(self, spec):
        raw = str(spec).strip();
        if raw == "0":
            for number in range(1, self.max_areas + 1):
                if self.areas[number].table is None:
                    self.active_area = number;
                    return number;
            raise DatabaseError("No free work area");
        if raw.isdigit():
            number = int(raw);
        elif len(raw) == 1 and raw.isalpha():
            number = ord(raw.upper()) - ord("A") + 1;
        else:
            number = None;
            for item in self.areas.values():
                if item.table is not None and (str(item.alias or "").upper() == raw.upper() or str(item.table).upper() == raw.upper()):
                    number = item.number;
                    break;
            if number is None:
                raise DatabaseError("Unknown work area/alias: {}".format(spec));
        if number < 1 or number > self.max_areas:
            raise DatabaseError("Work area must be 1..{} (A..Z aliases are accepted)".format(self.max_areas));
        self.active_area = number;
        return number;

    def use(self, table=None, alias=None):
        area = self.current_area;
        if not table:
            area.table = None;
            area.alias = None;
            area.recno = 0;
            area.relation = None;
            return area;
        if not self.source_exists(table):
            raise DatabaseError("Table/view not found: {}".format(table));
        area.table = str(table);
        area.alias = str(alias) if alias else str(table);
        area.recno = 1 if self.reccount(area=area) else 0;
        area.relation = None;
        return area;

    def _require_table(self, table=None):
        name = table or self.current_area.table;
        if not name:
            raise DatabaseError("No table open in work area {}".format(self.active_area));
        return str(name);

    def parse_column(self, definition):
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s+([A-Za-z]+)(?:\s*\(([^)]*)\))?(.*)$", definition.strip(), re.S);
        if not match:
            raise DatabaseError("Invalid column definition: {}".format(definition));
        name, type_name, params, tail = match.groups();
        declared = type_name.upper();
        key = declared;
        length = None;
        precision = None;
        scale = None;
        autoinum = False;
        if key in ("AUTONUM", "AUTOINCREMENT", "IDENTITY", "SERIAL"):
            logical = "INTEGER"; sqlite_type = "INTEGER"; autoinum = True;
        elif key in ("INTEGER", "INT", "I"):
            logical = "INTEGER"; sqlite_type = "INTEGER";
        elif key in ("NUMERIC", "NUMBER", "DECIMAL", "N", "CURRENCY", "MONEY"):
            logical = "NUMERIC"; sqlite_type = "INTEGER";
            if key in ("CURRENCY", "MONEY"):
                precision, scale = 19, 4;
            else:
                parts = [part.strip() for part in (params or "18,0").split(",")];
                precision = int(parts[0]);
                scale = int(parts[1]) if len(parts) > 1 else 0;
        elif key in ("FLOAT", "REAL", "DOUBLE", "F"):
            logical = "FLOAT"; sqlite_type = "REAL";
        elif key in ("CHARACTER", "CHAR", "C"):
            logical = "CHARACTER"; sqlite_type = "TEXT"; length = int(params or 1);
        elif key == "VARCHAR":
            logical = "VARCHAR"; sqlite_type = "TEXT"; length = int(params or 255);
        elif key in ("MEMO", "M"):
            logical = "MEMO"; sqlite_type = "TEXT"; length = 65535;
        elif key == "TEXT":
            logical = "TEXT"; sqlite_type = "TEXT";
        elif key in ("LOGICAL", "BOOL", "BOOLEAN", "L"):
            logical = "LOGICAL"; sqlite_type = "INTEGER";
        elif key in ("DATE", "D"):
            logical = "DATE"; sqlite_type = "TEXT";
        elif key == "TIME":
            logical = "TIME"; sqlite_type = "TEXT";
        elif key in ("DATETIME", "TIMESTAMP"):
            logical = "DATETIME"; sqlite_type = "TEXT";
        elif key in ("BLOB", "BINARY", "BYTE", "BYTES", "GENERAL", "G"):
            logical = "BLOB"; sqlite_type = "BLOB";
        elif key == "UUID":
            logical = "UUID"; sqlite_type = "TEXT"; length = 36;
        elif key == "JSON":
            logical = "JSON"; sqlite_type = "TEXT";
        else:
            raise DatabaseError("Unknown sumX type: {}".format(type_name));
        upper_tail = tail.upper();
        nullable = "NOT NULL" not in upper_tail;
        primary = autoinum or "PRIMARY KEY" in upper_tail;
        if primary:
            nullable = False;
        unique = "UNIQUE" in upper_tail;
        default_sql = None;
        default_match = re.search(r"(?i)\bDEFAULT\s+((?:'[^']*'|\"[^\"]*\"|[^\s,]+))", tail);
        if default_match:
            default_sql = default_match.group(1);
            if logical == "LOGICAL":
                if default_sql.upper() in ("TRUE", ".T.", "ON"):
                    default_sql = "1";
                elif default_sql.upper() in ("FALSE", ".F.", "OFF"):
                    default_sql = "0";
            if logical == "NUMERIC":
                try:
                    from decimal import Decimal;
                    default_sql = str(int(Decimal(default_sql) * (10 ** int(scale or 0))));
                except Exception:
                    pass;
        ref_table = None; ref_column = None;
        ref = re.search(r"(?i)\bREFERENCES\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)", tail);
        if ref:
            ref_table, ref_column = ref.groups();
        return ColumnDef(name, logical, declared, sqlite_type, length, precision, scale, nullable, default_sql, primary, unique, autoinum, ref_table, ref_column);

    def create_table(self, name, definitions):
        name = str(name);
        columns = [self.parse_column(item) for item in definitions];
        sql_columns = [];
        for col in columns:
            part = '{} {}'.format(quote_ident(col.name), col.sqlite_type);
            if col.autoinum:
                part += " PRIMARY KEY AUTOINCREMENT";
            else:
                if col.primary_key:
                    part += " PRIMARY KEY";
                if not col.nullable:
                    part += " NOT NULL";
                if col.unique:
                    part += " UNIQUE";
            if col.default_sql is not None:
                part += " DEFAULT {}".format(col.default_sql);
            if col.length is not None:
                part += " CHECK(length({}) <= {})".format(quote_ident(col.name), int(col.length));
            if col.logical_type == "LOGICAL":
                part += " CHECK({0} IN (0,1) OR {0} IS NULL)".format(quote_ident(col.name));
            if col.references_table:
                part += " REFERENCES {}({})".format(quote_ident(col.references_table), quote_ident(col.references_column));
            sql_columns.append(part);
        sql = "CREATE TABLE {} ({})".format(quote_ident(name), ", ".join(sql_columns));
        self.connection.execute(sql);
        self.connection.execute("DELETE FROM __sumx_columns WHERE table_name=?", (name,));
        for ordinal, col in enumerate(columns):
            self.connection.execute("INSERT INTO __sumx_columns VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                name, ordinal, col.name, col.logical_type, col.declared_type, col.sqlite_type, col.length, col.precision, col.scale,
                1 if col.nullable else 0, col.default_sql, 1 if col.primary_key else 0, 1 if col.unique else 0,
                1 if col.autoinum else 0, col.references_table, col.references_column,
            ));
        self.connection.commit();
        return columns;

    def columns(self, table=None):
        table = self._require_table(table);
        rows = self.connection.execute("SELECT * FROM __sumx_columns WHERE table_name=? ORDER BY ordinal", (table,)).fetchall();
        if not rows:
            pragma = self.connection.execute("PRAGMA table_info({})".format(quote_ident(table))).fetchall();
            return [ColumnDef(row[1], "TEXT", "TEXT", str(row[2] or "TEXT"), nullable=not bool(row[3]), primary_key=bool(row[5])) for row in pragma];
        return [ColumnDef(
            row["name"], row["logical_type"], row["declared_type"], row["sqlite_type"], row["length"],
            row["precision_value"], row["scale_value"], bool(row["nullable"]), row["default_sql"],
            bool(row["primary_key"]), bool(row["unique_value"]), bool(row["autoinum"]),
            row["references_table"], row["references_column"],
        ) for row in rows];

    def create_index(self, name, table, expression, unique=False):
        prefix = "CREATE UNIQUE INDEX" if unique else "CREATE INDEX";
        sql = "{} {} ON {} ({})".format(prefix, quote_ident(name), quote_ident(table), expression);
        self.connection.execute(sql);
        self.connection.commit();

    def create_view(self, name, select_sql, replace=False):
        name = str(name);
        sql = str(select_sql or "").strip().rstrip(";").strip();
        if not re.match(r"(?is)^(?:SELECT|WITH)\b", sql):
            raise DatabaseError("CREATE VIEW expects a SELECT/WITH query");
        if replace and self.view_exists(name):
            self.connection.execute("DROP VIEW {}".format(quote_ident(name)));
        self.connection.execute("CREATE VIEW {} AS {}".format(quote_ident(name), sql));
        self.connection.commit();
        return name;

    def create_relation(self, name, source_table, source_column, target_table, target_column):
        name = str(name);
        source_table = str(source_table);
        source_column = str(source_column);
        target_table = str(target_table);
        target_column = str(target_column);
        if not self.source_exists(source_table):
            raise DatabaseError("Source table/view not found: {}".format(source_table));
        if not self.source_exists(target_table):
            raise DatabaseError("Target table/view not found: {}".format(target_table));
        source_names = {col.name.casefold() for col in self.columns(source_table)};
        target_names = {col.name.casefold() for col in self.columns(target_table)};
        if source_column.casefold() not in source_names:
            raise DatabaseError("Column not found: {}.{}".format(source_table, source_column));
        if target_column.casefold() not in target_names:
            raise DatabaseError("Column not found: {}.{}".format(target_table, target_column));
        self.connection.execute(
            "INSERT OR REPLACE INTO __sumx_relations(name,source_table,source_column,target_table,target_column) VALUES (?,?,?,?,?)",
            (name, source_table, source_column, target_table, target_column),
        );
        self.connection.commit();
        return name;

    def relation_rows(self):
        rows = self.connection.execute(
            "SELECT name,source_table,source_column,target_table,target_column FROM __sumx_relations ORDER BY name"
        ).fetchall();
        output = [[row[0], row[1], row[2], row[3], row[4]] for row in rows];
        # Surface SQLite foreign keys as relationships too, even if they were
        # declared directly in CREATE TABLE rather than with LINK/RELATION.
        known = {(str(row[1]).casefold(), str(row[2]).casefold(), str(row[3]).casefold(), str(row[4]).casefold()) for row in output};
        for table in self.list_tables():
            for fk in self.connection.execute("PRAGMA foreign_key_list({})".format(quote_ident(table))).fetchall():
                target_table = fk[2];
                source_column = fk[3];
                target_column = fk[4];
                key = (str(table).casefold(), str(source_column).casefold(), str(target_table).casefold(), str(target_column).casefold());
                if key not in known:
                    output.append(["<foreign-key>", table, source_column, target_table, target_column]);
                    known.add(key);
        return output;

    def create_form(self, name, table, title=None):
        columns = self.columns(table);
        definition = {
            "name": str(name), "table": str(table), "title": str(title or name),
            "fields": [
                {"name": col.name, "type": col.declared_type, "row": index + 2, "col": 4, "width": col.length or 20, "readonly": bool(col.autoinum)}
                for index, col in enumerate(columns)
            ],
        };
        self.connection.execute("INSERT OR REPLACE INTO __sumx_forms(name,table_name,title,definition_json) VALUES (?,?,?,?)", (str(name), str(table), str(title or name), json.dumps(definition)));
        self.connection.commit();
        return definition;

    def get_form(self, name):
        row = self.connection.execute("SELECT * FROM __sumx_forms WHERE UPPER(name)=UPPER(?)", (str(name),)).fetchone();
        if row is None:
            raise DatabaseError("Form not found: {}".format(name));
        return {"name": row["name"], "table": row["table_name"], "title": row["title"], "definition": json.loads(row["definition_json"])};

    def append(self, values=None, table=None):
        table = self._require_table(table);
        if self.is_view(table):
            raise DatabaseError("Cannot APPEND to view: {}".format(table));
        values = dict(values or {});
        columns = {col.name.upper(): col for col in self.columns(table)};
        encoded = {};
        for key, value in values.items():
            lookup = str(key).upper();
            if lookup not in columns:
                raise DatabaseError("Unknown column {}.{}".format(table, key));
            col = columns[lookup];
            if col.autoinum:
                continue;
            encoded[col.name] = col.encode(value);
        if not encoded:
            cursor = self.connection.execute("INSERT INTO {} DEFAULT VALUES".format(quote_ident(table)));
        else:
            names = list(encoded);
            placeholders = ",".join("?" for _ in names);
            sql = "INSERT INTO {} ({}) VALUES ({})".format(quote_ident(table), ",".join(quote_ident(name) for name in names), placeholders);
            cursor = self.connection.execute(sql, tuple(encoded[name] for name in names));
        self.connection.commit();
        area = self.current_area;
        if area.table == table:
            area.recno = self.reccount(area=area);
        return cursor.lastrowid;

    def record_at(self, recno=None, table=None):
        table = self._require_table(table);
        number = int(self.current_area.recno if recno is None else recno);
        if number <= 0:
            return {};
        order = "" if self.is_view(table) else " ORDER BY rowid";
        row = self.connection.execute(
            "SELECT * FROM {}{} LIMIT 1 OFFSET ?".format(quote_ident(table), order),
            (number - 1,),
        ).fetchone();
        if row is None:
            return {};
        cols = {col.name: col for col in self.columns(table)};
        return {name: cols[name].decode(value) if name in cols else value for name, value in dict(row).items()};

    def update_record(self, values, recno=None, table=None):
        table = self._require_table(table);
        if self.is_view(table):
            raise DatabaseError("Cannot EDIT view: {}".format(table));
        number = int(self.current_area.recno if recno is None else recno);
        if number <= 0:
            raise DatabaseError("No current record");
        rowid_row = self.connection.execute(
            "SELECT rowid FROM {} ORDER BY rowid LIMIT 1 OFFSET ?".format(quote_ident(table)),
            (number - 1,),
        ).fetchone();
        if rowid_row is None:
            raise DatabaseError("Record {} not found".format(number));
        columns = {col.name.casefold(): col for col in self.columns(table)};
        encoded = {};
        for key, value in dict(values or {}).items():
            lookup = str(key).casefold();
            if lookup not in columns:
                raise DatabaseError("Unknown column {}.{}".format(table, key));
            col = columns[lookup];
            if col.autoinum:
                continue;
            encoded[col.name] = col.encode(value);
        if encoded:
            names = list(encoded);
            sql = "UPDATE {} SET {} WHERE rowid=?".format(
                quote_ident(table),
                ",".join("{}=?".format(quote_ident(name)) for name in names),
            );
            params = [encoded[name] for name in names] + [rowid_row[0]];
            self.connection.execute(sql, params);
            self.connection.commit();
        if self.current_area.table == table:
            self.current_area.recno = number;
        return number;

    def find_record(self, text, table=None, start_recno=None):
        table = self._require_table(table);
        needle = str(text or "").casefold();
        if not needle:
            return 0;
        columns, rows = self.browse(table=table, limit=max(1, self.reccount_for(table)));
        count = len(rows);
        if not count:
            return 0;
        start = int(start_recno if start_recno is not None else self.current_area.recno or 0);
        for offset in range(count):
            index = (start + offset) % count;
            if any(needle in str(cell).casefold() for cell in rows[index]):
                return index + 1;
        return 0;

    def reccount_for(self, table):
        table = self._require_table(table);
        return int(self.connection.execute("SELECT COUNT(*) FROM {}".format(quote_ident(table))).fetchone()[0]);

    def reccount(self, area=None):
        area = area or self.current_area;
        table = area.table if area is not None else None;
        if not table:
            return 0;
        return int(self.connection.execute("SELECT COUNT(*) FROM {}".format(quote_ident(table))).fetchone()[0]);

    def recno(self):
        return int(self.current_area.recno or 0);

    def go(self, target):
        count = self.reccount();
        if count <= 0:
            self.current_area.recno = 0;
            return 0;
        if isinstance(target, str):
            key = target.upper();
            if key == "TOP":
                target = 1;
            elif key == "BOTTOM":
                target = count;
        number = max(1, min(count, int(target)));
        self.current_area.recno = number;
        return number;

    def skip(self, amount=1):
        if not self.current_area.recno:
            return self.go(1);
        return self.go(self.current_area.recno + int(amount));

    def current_record(self):
        return self.record_at(self.current_area.recno);

    def browse(self, table=None, limit=200):
        table = self._require_table(table);
        cols = self.columns(table);
        order = "" if self.is_view(table) else " ORDER BY rowid";
        rows = self.connection.execute("SELECT * FROM {}{} LIMIT ?".format(quote_ident(table), order), (max(1, int(limit)),)).fetchall();
        output = [];
        for row in rows:
            values = [];
            data = dict(row);
            for col in cols:
                values.append(col.display(data.get(col.name)));
            output.append(values);
        return [col.name for col in cols], output;

    def workareas_rows(self):
        rows = [];
        for area in self.areas.values():
            if area.table is None:
                continue;
            rows.append(["{}/{}".format(area.letter, area.number), area.alias or "", area.table, str(area.recno or 0), str(self.reccount(area=area)), area.relation or ""]);
        return rows;

    def status(self):
        db_name = ":memory:" if self.path == ":memory:" else Path(self.path).name;
        occupied = [];
        for area in self.areas.values():
            if area.table is None:
                continue;
            label = "{}/{}:{}={}".format(area.letter, area.number, area.alias, area.table) if area.alias and area.alias.casefold() != area.table.casefold() else "{}/{}:{}".format(area.letter, area.number, area.table);
            if area.number == self.active_area:
                label = "[{}]".format(label);
            occupied.append(label);
        current = self.current_area;
        record = "Rec {}/{}".format(current.recno or 0, self.reccount()) if current.table else "Rec -";
        relation = " | Rel {}".format(current.relation) if current.relation else "";
        areas = " ".join(occupied) if occupied else "no open tables";
        return "DB: {} | {} | {}{}".format(db_name, areas, record, relation);
