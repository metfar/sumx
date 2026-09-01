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


@dataclass
class OutputResult:
    text: str;
    level: str = "OUTPUT";
    channel: str = "stdout";
    emit: bool = True;


@dataclass
class TableResult:
    title: str;
    columns: list;
    rows: list;


@dataclass
class HelpRequest:
    text: str
    title: str = "sumX Help"


@dataclass
class BrowseRequest:
    title: str;
    columns: list;
    rows: list;
    table: str = None;
    readonly: bool = True;


@dataclass
class ScreenWriteResult:
    row: int;
    column: int;
    text: str;
    style: str = "command";
    window: str = None;


@dataclass
class GetField:
    target: str;
    row: int;
    column: int;
    width: int;
    value: str;
    original: object = None;
    fixed: bool = True;
    height: int = 1;
    picture: str = "";
    max_length: int = None;
    overflow: bool = False;
    window: str = None;
    valid: str = "";
    error: str = "";


@dataclass
class ScreenGetResult:
    field: GetField;


@dataclass
class ReadRequest:
    fields: list;
    remaining: list = None;


@dataclass
class InputRequest:
    prompt: str;
    target: str;
    command: str = "INPUT";
    text_only: bool = False;
    keys: str = "";
    case_sensitive: bool = False;
    default_character: str = "";
    timeout_seconds: float = None;
    width: int = None;
    height: int = 1;
    picture: str = "";
    hidden: bool = False;
    mask: str = None;
    dialog: bool = False;
    remaining: list = None;


@dataclass
class WindowRequest:
    action: str;
    name: str;
    definition: dict = None;


@dataclass
class ClearResult:
    pass;


@dataclass
class QuitResult:
    pass;


@dataclass
class ReturnResult:
    value: object = None;


@dataclass
class BatchResult:
    results: list;


@dataclass
class AppendRequest:
    table: str;
    columns: list;
    title: str = "Append";


@dataclass
class FormRequest:
    name: str;
    table: str;
    columns: list;
    title: str;
