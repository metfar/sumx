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

from rich.console import Console;

from sumtui import InputSpec, read_input;

from .console import print_result;
from .interpreter import Interpreter;
from .results import AppendRequest, BatchResult, FormRequest, InputRequest, QuitResult, ReadRequest, ReturnResult;


class GeneratedProgram:
    """Runtime helper used by readable Python emitted by ``sumx --compile``."""
    def __init__(self, source_name="<compiled>", database=":memory:"):
        self.source_name = str(source_name);
        self.interpreter = Interpreter(database=database);
        if self.source_name and not self.source_name.startswith("<"):
            try:
                self.interpreter.source_stack.append(Path(self.source_name).expanduser().resolve());
            except Exception:
                pass;
        self.console = Console();
        self.diagnostics = Console(stderr=True);
        self.stopped = False;
        self.exit_code = 0;

    def _handle(self, result):
        queue = [result];
        while queue and not self.stopped:
            item = queue.pop(0);
            if item is None:
                continue;
            if isinstance(item, BatchResult):
                queue = list(item.results) + queue;
                continue;
            if isinstance(item, (QuitResult, ReturnResult)):
                self.stopped = True;
                continue;
            if isinstance(item, (AppendRequest, FormRequest)):
                values = {};
                for column in item.columns:
                    if column.autoinum:
                        continue;
                    entered = input("{} [{}]: ".format(column.name, column.declared_type));
                    if entered != "":
                        values[column.name] = entered;
                self.interpreter.runtime.db.append(values, table=item.table);
                continue;
            if isinstance(item, InputRequest):
                spec = InputSpec(
                    prompt=item.prompt,
                    width=item.width,
                    height=item.height,
                    picture=item.picture,
                    overflow=self.interpreter.runtime.field_wrap_overflow,
                    hidden=item.hidden,
                    mask=item.mask,
                    keys=item.keys,
                    case_sensitive=item.case_sensitive,
                    default=item.default_character,
                    timeout=item.timeout_seconds,
                    dialog=item.dialog,
                    title="{} -> {}".format(item.command, item.target),
                );
                response = read_input(spec);
                if response.status == 1:
                    self.exit_code = 1;
                    self.stopped = True;
                    continue;
                self.interpreter.apply_input_value(item, response.value);
                if item.remaining:
                    continuation = self.interpreter.execute_remaining(item.remaining, interactive=False);
                    if continuation is not None:
                        queue.insert(0, continuation);
                continue;
            if isinstance(item, ReadRequest):
                values = {};
                for field in item.fields:
                    entered = input("{} [{}]: ".format(field.target, field.value.rstrip()));
                    values[field.target] = entered if entered != "" else field.value;
                self.interpreter.apply_read_values(item.fields, values);
                if item.remaining:
                    continuation = self.interpreter.execute_remaining(item.remaining, interactive=False);
                    if continuation is not None:
                        queue.insert(0, continuation);
                continue;
            print_result(self.console, item, error_console=self.diagnostics);
        return not self.stopped;

    def condition(self, expression, source_line=None):
        if self.stopped:
            return False;
        try:
            return bool(self.interpreter.evaluate(str(expression)));
        except Exception as exc:
            line = "" if source_line is None else ":{}".format(source_line);
            self.diagnostics.print("{}{}: {}".format(self.source_name, line, exc), style="bold red");
            self.exit_code = 1;
            self.stopped = True;
            return False;

    def statement(self, source, source_line=None):
        if self.stopped:
            return False;
        try:
            result = self.interpreter.execute(str(source), interactive=False);
            return self._handle(result);
        except Exception as exc:
            line = "" if source_line is None else ":{}".format(source_line);
            self.diagnostics.print("{}{}: {}".format(self.source_name, line, exc), style="bold red");
            self.exit_code = 1;
            self.stopped = True;
            return False;

    def finish(self):
        try:
            self.interpreter.runtime.db.close();
        except Exception:
            pass;
        return int(self.exit_code);
