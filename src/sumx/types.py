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
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN;


class SumXTypeError(ValueError):
    pass;


@dataclass
class ColumnDef:
    name: str;
    logical_type: str;
    declared_type: str;
    sqlite_type: str;
    length: int = None;
    precision: int = None;
    scale: int = None;
    nullable: bool = True;
    default_sql: str = None;
    primary_key: bool = False;
    unique: bool = False;
    autoinum: bool = False;
    references_table: str = None;
    references_column: str = None;

    @property
    def multiline(self):
        return self.declared_type.upper() == "MEMO";

    @property
    def binary(self):
        return self.logical_type == "BLOB";

    def encode(self, value):
        if value is None:
            return None;
        if self.logical_type == "NUMERIC":
            try:
                number = value if isinstance(value, Decimal) else Decimal(str(value));
            except InvalidOperation as exc:
                raise SumXTypeError("{} expects NUMERIC".format(self.name)) from exc;
            scale = int(self.scale or 0);
            quantum = Decimal(1).scaleb(-scale);
            number = number.quantize(quantum, rounding=ROUND_HALF_EVEN);
            if self.precision is not None:
                digits = len(number.as_tuple().digits);
                if digits > int(self.precision):
                    raise SumXTypeError("{} exceeds NUMERIC({}, {})".format(self.name, self.precision, scale));
            return int(number * (10 ** scale));
        if self.logical_type == "LOGICAL":
            if isinstance(value, str):
                key = value.strip().upper();
                if key in ("TRUE", "T", ".T.", "ON", "1", "Y", "YES"):
                    return 1;
                if key in ("FALSE", "F", ".F.", "OFF", "0", "N", "NO"):
                    return 0;
                raise SumXTypeError("{} expects LOGICAL".format(self.name));
            return 1 if bool(value) else 0;
        if self.logical_type in ("CHARACTER", "VARCHAR", "MEMO", "TEXT", "DATE", "TIME", "DATETIME", "UUID", "JSON"):
            text = str(value);
            if self.length is not None and len(text) > int(self.length):
                raise SumXTypeError("{} exceeds {} characters".format(self.name, self.length));
            return text;
        if self.logical_type == "INTEGER":
            return int(value);
        if self.logical_type == "FLOAT":
            return float(value);
        if self.logical_type == "BLOB":
            if isinstance(value, memoryview):
                return bytes(value);
            if isinstance(value, (bytes, bytearray)):
                return bytes(value);
            raise SumXTypeError("{} expects bytes/BLOB".format(self.name));
        return value;

    def decode(self, value):
        if value is None:
            return None;
        if self.logical_type == "NUMERIC":
            scale = int(self.scale or 0);
            return Decimal(int(value)) / Decimal(10 ** scale);
        if self.logical_type == "LOGICAL":
            return bool(value);
        if self.logical_type == "BLOB":
            return bytes(value);
        return value;

    def display(self, value):
        decoded = self.decode(value);
        if decoded is None:
            return "";
        if self.logical_type == "LOGICAL":
            return "TRUE" if decoded else "FALSE";
        if self.logical_type == "NUMERIC":
            scale = int(self.scale or 0);
            return format(decoded, ".{}f".format(scale));
        if self.logical_type == "BLOB":
            return "<{} bytes>".format(len(decoded));
        return str(decoded);
