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

from sumtui import Button, CommandWindow, Dialog, FileDialog, FunctionBar, HBox, Menu, MenuBar, MenuDesktop, MenuItem, Panel, Separator, StatusBar, TextEditor, TextInput, VBox;
from sumtui.document import TextDocument;

from .compiler import check_source, compile_source;
from .console import SumXConsoleApp;
from .helpdb import find_topic;


class SumXEditorApp(SumXConsoleApp):
    """Keyboard-first educational source editor for .PRG files."""
    def __init__(self, path, interpreter=None, database=":memory:", theme="XBASE"):
        self.path = Path(path).expanduser().resolve();
        if not self.path.exists():
            self.document = TextDocument.empty(self.path);
        else:
            self.document = TextDocument.load(self.path);
        source = self.document.text;
        super().__init__(interpreter=interpreter, database=database, theme=theme);
        self.editor = TextEditor(source, line_numbers=True, on_change=self._editor_changed, on_cursor=self._editor_changed);
        self.command = CommandWindow(prompt=". ", on_submit=self._submit);
        self.interpreter.runtime.set_screen_size_provider(self._screen_size);
        self.status = StatusBar("");
        self.search_text = "";
        self.app.bindings = {};
        self.app.unbind("ctrl+c");
        self.menu = MenuBar(self._editor_menus(), on_close=self._menu_closed);
        self.bar = FunctionBar([
            ("f1", "Help", self._editor_help),
            ("f2", "Save", self.save),
            ("f5", "Run", self.run_buffer),
            ("f6", "Compile", self.compile_buffer),
            ("f9", "Menu", self.open_menu),
            ("f10", "Exit", self.app.stop),
        ]);
        self.bar.install(self.app);
        self.app.bind("ctrl+f9", self.run_buffer);
        self.app.bind("alt+f9", self.check_buffer);
        self.app.bind("ctrl+n", self.new_file);
        self.app.bind("ctrl+o", self.open_file_dialog);
        self.app.bind("ctrl+s", self.save);
        self.app.bind("alt+x", self.app.stop);
        self.app.bind("ctrl+f", self.find_dialog);
        self.app.bind("f3", self.find_next);
        self.app.bind("shift+f3", self.find_previous);
        self.app.bind("ctrl+g", self.goto_line_dialog);
        for key, index in (("alt+f", 0), ("alt+e", 1), ("alt+s", 2), ("alt+r", 3), ("alt+d", 4), ("alt+o", 5), ("alt+h", 6)):
            self.app.bind(key, lambda index=index: self.open_menu(index));
        self.editor_panel = Panel(self.editor, title=self.path.name, content_style="viewer");
        self.output_panel = Panel(self.command, title="Output / Command", content_style="command");
        body = VBox(
            self.editor_panel,
            self.output_panel,
            self.status,
            self.bar,
            sizes=[None, 9, 1, 1],
        );
        self.desktop = MenuDesktop(self.menu, body);
        self.app.set_root(self.desktop);
        self.app.focus.set(self.editor);
        self._update_editor_status();

    def _editor_menus(self):
        return [
            Menu("File", [
                MenuItem("New", self.new_file, "Ctrl+N"),
                MenuItem("Open...", self.open_file_dialog, "Ctrl+O"),
                MenuItem("Save", self.save, "F2"),
                MenuItem("Save As...", self.save_as_dialog),
                Separator(),
                MenuItem("Exit", self.app.stop, "F10"),
            ]),
            Menu("Edit", [
                MenuItem("Undo", self.editor.undo, "Ctrl+Z"),
                MenuItem("Redo", self.editor.redo, "Ctrl+Y"),
                Separator(),
                MenuItem("Cut", self.editor.cut, "Ctrl+X"),
                MenuItem("Copy", self.editor.copy, "Ctrl+C"),
                MenuItem("Paste", self.editor.paste, "Ctrl+V"),
                Separator(),
                MenuItem("Select All", self.editor.select_all, "Ctrl+A"),
            ]),
            Menu("Search", [
                MenuItem("Find...", self.find_dialog, "Ctrl+F"),
                MenuItem("Find Next", self.find_next, "F3"),
                MenuItem("Find Previous", self.find_previous, "Shift+F3"),
                MenuItem("Replace...", enabled=False),
                Separator(),
                MenuItem("Go to Line...", self.goto_line_dialog, "Ctrl+G"),
            ]),
            Menu("Run", [
                MenuItem("Check", self.check_buffer, "Alt+F9"),
                MenuItem("Run", self.run_buffer, "Ctrl+F9"),
                MenuItem("Compile to Python", self.compile_buffer, "F6"),
            ]),
            Menu("Debug", [
                MenuItem("Run to Cursor", enabled=False, shortcut="F4"),
                MenuItem("Trace Into", enabled=False, shortcut="F7"),
                MenuItem("Step Over", enabled=False, shortcut="F8"),
                MenuItem("Toggle Breakpoint", enabled=False),
                MenuItem("Reset", enabled=False, shortcut="Ctrl+F2"),
            ]),
            Menu("Options", [
                MenuItem("Show spaces", self.toggle_spaces, checked=lambda: self.editor.show_spaces),
                MenuItem("Show tabs", self.toggle_tabs, checked=lambda: self.editor.show_tabs),
                MenuItem("Show line endings", self.toggle_eols, checked=lambda: self.editor.show_line_endings),
                MenuItem("Show control characters", self.toggle_controls, checked=lambda: self.editor.show_control_chars),
            ]),
            Menu("Help", [
                MenuItem("Context Help", self._editor_help, "F1"),
                MenuItem("sumX Help", self._help),
                MenuItem("Editor Keys", self._editor_keys_help),
            ]),
        ];

    def open_menu(self, index=None):
        if index is None:
            index = self.menu.menu_index;
        self.menu.open(index);
        self.app.focus.set(self.menu);
        self.app.invalidate();
        return True;

    def _menu_closed(self):
        self.app.focus.set(self.editor);
        self.app.invalidate();
        return True;

    def _set_document(self, document, path=None):
        self.document = document;
        if path is not None:
            self.path = Path(path).expanduser().resolve();
            self.document.path = self.path;
        elif self.document.path is not None:
            self.path = Path(self.document.path).expanduser().resolve();
        self.editor.set_text(self.document.text, modified=False);
        self.editor_panel.title = self.path.name;
        self.app.focus.set(self.editor);
        self._update_editor_status("Loaded");
        return True;

    def new_file(self):
        target = Path.cwd() / "untitled.prg";
        return self._set_document(TextDocument.empty(target), target);

    def open_file_dialog(self):
        start = self.path.parent if self.path is not None else Path.cwd();
        def close():
            self.app.pop_modal();
            self.app.focus.set(self.editor);
            self.app.invalidate();
        def accepted(path):
            try:
                document = TextDocument.load(path);
                close();
                self._set_document(document, path);
            except Exception as exc:
                close();
                self._update_editor_status("Open error: {}".format(exc));
        dialog = FileDialog(path=start, title="Open sumX source", on_accept=accepted, on_cancel=close, theme=self.app.theme);
        self.app.push_modal(dialog);
        self.app.invalidate();
        return True;

    def save_as_dialog(self):
        entry = TextInput(str(self.path));
        def close():
            self.app.pop_modal();
            self.app.focus.set(self.editor);
            self.app.invalidate();
        def accepted(*_args):
            self.path = Path(entry.value).expanduser().resolve();
            self.document.path = self.path;
            self.editor_panel.title = self.path.name;
            close();
            self.save();
        body = VBox(entry, HBox(Button("Save", on_press=accepted, default=True), Button("Cancel", on_press=close), ratios=[1, 1]), sizes=[1, 1]);
        self.app.push_modal(Dialog(body, title="Save As", width=72, height=7, on_cancel=close));
        self.app.focus.set(entry);
        self.app.invalidate();
        return True;

    def find_dialog(self):
        entry = TextInput(self.search_text);
        def close():
            self.app.pop_modal();
            self.app.focus.set(self.editor);
            self.app.invalidate();
        def accepted(*_args):
            self.search_text = entry.value;
            close();
            return self.find_next();
        body = VBox(entry, HBox(Button("Find", on_press=accepted, default=True), Button("Cancel", on_press=close), ratios=[1, 1]), sizes=[1, 1]);
        self.app.push_modal(Dialog(body, title="Find", width=56, height=7, on_cancel=close));
        self.app.focus.set(entry);
        self.app.invalidate();
        return True;

    def _select_match(self, start, end):
        self.editor.anchor = self.editor._position(start);
        self.editor.row, self.editor.column = self.editor._position(end);
        self.editor.preferred_column = self.editor.column;
        self.editor._ensure_visible();
        self.editor._notify_cursor();
        self.app.focus.set(self.editor);
        self.app.invalidate();
        return True;

    def find_next(self):
        needle = str(self.search_text or "");
        if not needle:
            return self.find_dialog();
        text = self.editor.text;
        start = self.editor._offset();
        found = text.find(needle, start);
        if found < 0 and start > 0:
            found = text.find(needle, 0, start);
        if found < 0:
            self._update_editor_status("Not found: {}".format(needle));
            return False;
        self._select_match(found, found + len(needle));
        self._update_editor_status("Found: {}".format(needle));
        return True;

    def find_previous(self):
        needle = str(self.search_text or "");
        if not needle:
            return self.find_dialog();
        text = self.editor.text;
        start = self.editor._offset();
        found = text.rfind(needle, 0, max(0, start));
        if found < 0:
            found = text.rfind(needle);
        if found < 0:
            self._update_editor_status("Not found: {}".format(needle));
            return False;
        self._select_match(found, found + len(needle));
        self._update_editor_status("Found: {}".format(needle));
        return True;

    def goto_line_dialog(self):
        entry = TextInput(str(self.editor.cursor_line));
        def close():
            self.app.pop_modal();
            self.app.focus.set(self.editor);
            self.app.invalidate();
        def accepted(*_args):
            try:
                line = max(1, int(entry.value));
            except ValueError:
                self._update_editor_status("Invalid line number");
                close();
                return False;
            close();
            row = min(len(self.editor.lines) - 1, line - 1);
            self.editor._apply_move(row, 0);
            self._update_editor_status();
            return True;
        body = VBox(entry, HBox(Button("Go", on_press=accepted, default=True), Button("Cancel", on_press=close), ratios=[1, 1]), sizes=[1, 1]);
        self.app.push_modal(Dialog(body, title="Go to Line", width=36, height=7, on_cancel=close));
        self.app.focus.set(entry);
        self.app.invalidate();
        return True;

    def toggle_spaces(self):
        self.editor.show_spaces = not self.editor.show_spaces;
        self.app.invalidate();
        return True;

    def toggle_tabs(self):
        self.editor.show_tabs = not self.editor.show_tabs;
        self.app.invalidate();
        return True;

    def toggle_eols(self):
        self.editor.show_line_endings = not self.editor.show_line_endings;
        self.app.invalidate();
        return True;

    def toggle_controls(self):
        self.editor.show_control_chars = not self.editor.show_control_chars;
        self.app.invalidate();
        return True;

    def _editor_keys_help(self):
        text = """# sumX editor keys

- **F9** opens the top menu; **F10** exits.
- **F1** contextual help; **F2** save; **F5** run; **F6** compile to Python.
- **Ctrl+F9** runs the current buffer; **Alt+F9** checks it.
- **Ctrl+Z / Ctrl+Y** undo/redo.
- **Ctrl+C / Ctrl+X / Ctrl+V** copy/cut/paste.
- **Shift+movement** extends selection.
- **Ctrl+Left / Ctrl+Right** move by words; add Shift to extend selection.
- **Ctrl+F**, **F3**, **Shift+F3** search; **Ctrl+G** goes to a line.

The File/Edit/Search/Run/Debug/Options/Help menus remain visible at the top. Debug commands are placeholders until the debugger runtime is implemented.
""";
        self._show_help(text, title="sumX Editor Help");
        return True;

    def _editor_changed(self, _editor):
        self._update_editor_status();
        return True;

    def _update_editor_status(self, message=None):
        marker = "*" if self.editor.modified else "";
        eol = self.document.eol if hasattr(self, "document") else "LF";
        encoding = self.document.encoding_label if hasattr(self, "document") else "UTF-8";
        selected = "  Sel {}".format(self.editor.selection_length) if self.editor.has_selection else "";
        base = "{}{}  Ln {}, Col {}{}  {}  {}".format(self.path.name, marker, self.editor.cursor_line, self.editor.cursor_column, selected, encoding, eol);
        if message:
            base += "  |  " + str(message);
        self.status.set(base);
        self.app.invalidate();
        return base;

    def _update_status(self):
        if hasattr(self, "editor"):
            self._update_editor_status();
        else:
            super()._update_status();

    def save(self):
        self.document.path = self.path;
        self.document.text = self.editor.text;
        self.document.save(text=self.editor.text);
        self.editor.mark_saved();
        self._update_editor_status("Saved");
        return True;

    def check_buffer(self):
        try:
            statements = check_source(self.editor.text);
            self.command.write("Check OK: {} statement(s)".format(len(statements)), style="command_info");
            self._update_editor_status("Check OK");
        except Exception as exc:
            self.command.write_error("Check error: {}".format(exc));
            self._update_editor_status("Check failed");
        self.app.invalidate();
        return True;

    def run_buffer(self):
        if self._program_active:
            self.command.write_error("A program is already running");
            return False;
        self.command.write("--- Run {} ---".format(self.path.name), style="command_info");
        self.run_program(self.editor.text, name=str(self.path));
        self.app.invalidate();
        return True;

    def compile_buffer(self):
        try:
            generated = compile_source(self.editor.text, source_name=str(self.path));
            output = self.path.with_suffix(".py");
            output.write_text(generated, encoding="utf-8");
            try:
                output.chmod(output.stat().st_mode | 0o111);
            except OSError:
                pass;
            self.command.write("Compiled -> {}".format(output), style="command_info");
            self._update_editor_status("Compiled");
            return True;
        except Exception as exc:
            self.command.write_error("Compile error: {}".format(exc));
            self._update_editor_status("Compile failed");
            return False;

    def _token_under_cursor(self):
        line = self.editor.lines[self.editor.row] if self.editor.lines else "";
        column = max(0, min(len(line), self.editor.column));
        start = column;
        end = column;
        while start > 0 and (line[start - 1].isalnum() or line[start - 1] in "_!"):
            start -= 1;
        while end < len(line) and (line[end].isalnum() or line[end] in "_!"):
            end += 1;
        return line[start:end];

    def _editor_help(self):
        token = self._token_under_cursor();
        topic = find_topic(token);
        if topic is None:
            return self._help();
        self._show_help(topic.markdown(), title="sumX Help - {}".format(topic.name));
        return True;

    def _begin_read(self, request, after_done=None):
        result = super()._begin_read(request, after_done=after_done);
        self.app.focus.set(self.command);
        return result;

    def _finish_program(self):
        result = super()._finish_program();
        if hasattr(self, "editor"):
            self.app.focus.set(self.editor);
            self._update_editor_status("Run finished");
        return result;
