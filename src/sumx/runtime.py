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
import shutil;

from .database import SumXDatabase;
from .sql import execute_sql;


class Runtime:
    DEBUG_LEVELS = {"OFF": 0, "INFO": 1, "DEBUG": 2, "TRACE": 3};

    def __init__(self, database=":memory:", max_areas=32, debug_level="OFF"):
        self.variables = {};
        self.caps_sensitive = False;
        self.debug_level = "OFF";
        self.field_wrap_overflow = False;
        self.line_continuation = "BACKSLASH";
        self.ampersand_comment = False;
        self.windows = {};
        self.active_window = None;
        self._screen_size_provider = None;
        self.set_debug_level(debug_level);
        self.db = SumXDatabase(database, max_areas=max_areas);


    def set_line_continuation(self, mode):
        key = str(mode or "BACKSLASH").strip().upper();
        if key not in ("BACKSLASH", "SEMICOLON"):
            raise ValueError("LINE_CONTINUATION expects BACKSLASH or SEMICOLON");
        self.line_continuation = key;
        return self.line_continuation;

    def set_ampersand_comment(self, enabled):
        self.ampersand_comment = bool(enabled);
        return self.ampersand_comment;

    def define_window(self, name, definition):
        key = str(name);
        self.windows[key.casefold()] = dict(definition, name=key);
        return self.windows[key.casefold()];

    def get_window(self, name):
        key = str(name).casefold();
        if key not in self.windows:
            raise KeyError("Unknown window: {}".format(name));
        return self.windows[key];

    def activate_window(self, name):
        definition = self.get_window(name);
        self.active_window = definition["name"];
        return definition;

    def deactivate_window(self, name=None):
        if name is not None and self.active_window is not None and str(name).casefold() != str(self.active_window).casefold():
            raise KeyError("Window is not active: {}".format(name));
        previous = self.active_window;
        self.active_window = None;
        return previous;

    def release_window(self, name):
        key = str(name).casefold();
        definition = self.get_window(name);
        if self.active_window is not None and str(self.active_window).casefold() == key:
            self.active_window = None;
        del self.windows[key];
        return definition;

    def set_field_wrap_overflow(self, enabled):
        self.field_wrap_overflow = bool(enabled);
        return self.field_wrap_overflow;

    def set_screen_size_provider(self, provider):
        self._screen_size_provider = provider if callable(provider) else None;
        return self._screen_size_provider;

    def screen_size(self):
        if self._screen_size_provider is not None:
            try:
                size = self._screen_size_provider();
                if size is not None:
                    columns, rows = size;
                    return max(1, int(columns)), max(1, int(rows));
            except Exception:
                pass;
        size = shutil.get_terminal_size(fallback=(80, 25));
        return max(1, int(size.columns)), max(1, int(size.lines));

    def set_debug_level(self, level):
        if isinstance(level, bool):
            level = "INFO" if level else "OFF";
        raw = str(level).strip().upper();
        aliases = {
            "0": "OFF", "OFF": "OFF", "FALSE": "OFF", ".F.": "OFF", "QUIET": "OFF", "NONE": "OFF",
            "1": "INFO", "ON": "INFO", "TRUE": "INFO", ".T.": "INFO", "INFO": "INFO",
            "2": "DEBUG", "DEBUG": "DEBUG",
            "3": "TRACE", "TRACE": "TRACE",
        };
        if raw not in aliases:
            raise ValueError("DEBUG_LEVEL expects OFF, INFO, DEBUG or TRACE");
        self.debug_level = aliases[raw];
        return self.debug_level;

    def debug_enabled(self, level="INFO"):
        raw = str(level).strip().upper();
        required = self.DEBUG_LEVELS.get(raw);
        if required is None:
            raise ValueError("Unknown debug level: {}".format(level));
        return self.DEBUG_LEVELS[self.debug_level] >= required;

    def _find_variable_name(self, name):
        raw = str(name);
        if self.caps_sensitive:
            return raw if raw in self.variables else None;
        folded = raw.casefold();
        matches = [key for key in self.variables if key.casefold() == folded];
        if not matches:
            return None;
        if len(matches) > 1:
            raise NameError("Ambiguous variable while CAPS_SENSITIVE is OFF: {}".format(name));
        return matches[0];

    def set_caps_sensitive(self, enabled):
        enabled = bool(enabled);
        if not enabled:
            seen = {};
            for name in self.variables:
                folded = name.casefold();
                if folded in seen and seen[folded] != name:
                    raise ValueError("Cannot SET CAPS_SENSITIVE OFF: variables {} and {} collide".format(seen[folded], name));
                seen[folded] = name;
        self.caps_sensitive = enabled;
        return self.caps_sensitive;

    def set_value(self, name, value):
        raw = str(name);
        existing = self._find_variable_name(raw);
        key = existing if existing is not None else raw;
        self.variables[key] = value;
        return value;

    def get_value(self, name):
        key = self._find_variable_name(name);
        if key is not None:
            return self.variables[key];
        record = self.db.current_record() if self.db.current_area.table else {};
        folded = str(name).casefold();
        for field, value in record.items():
            if str(field).casefold() == folded:
                return value;
        raise NameError("Unknown variable/field: {}".format(name));

    def has_value(self, name):
        return self._find_variable_name(name) is not None;

    def execute_sql(self, sql, mode="AUTO", params=None):
        return execute_sql(self, sql, mode=mode, params=params);
