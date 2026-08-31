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

from sumtui import Button, CommandWindow, CommandWindowPane, Dialog, FileDialog, FunctionBar, HBox, Label, ListView, Menu, MenuBar, MenuDesktop, MenuItem, Separator, StatusBar, TextEditor, TextInput, TextView, TextViewPane, VBox, Workspace, WorkspaceWindow;
from sumtui.document import TextDocument;
from sumtui.symbols import build_symbol_map, symbol_index_for_line;

from .compiler import check_source, compile_source;
from .console import SumXConsoleApp;
from .helpdb import find_topic;
from .results import OutputResult;


class SumXEditorApp(SumXConsoleApp):
    """Keyboard-first educational source editor for .PRG files."""
    def __init__(self, path, interpreter=None, database=":memory:", theme=None, config_path=None, config=None):
        self.path = Path(path).expanduser().resolve();
        if not self.path.exists():
            self.document = TextDocument.empty(self.path);
        else:
            self.document = TextDocument.load(self.path);
        source = self.document.text;
        super().__init__(interpreter=interpreter, database=database, theme=theme, config_path=config_path, config=config);
        editor_config = self.config.get("editor", {}) if isinstance(self.config.get("editor"), dict) else {};
        self.editor = TextEditor(source, line_numbers=True, on_change=self._editor_changed, on_cursor=self._editor_changed);
        self.editor.configure_visibility(
            spaces=bool(editor_config.get("show_spaces", False)),
            tabs=bool(editor_config.get("show_tabs", False)),
            line_endings=bool(editor_config.get("show_line_endings", False)),
            controls=bool(editor_config.get("show_control_chars", False)),
        );
        self.command = CommandWindow(prompt=". ", on_submit=self._submit);
        self.interpreter.runtime.set_screen_size_provider(self._screen_size);
        self.status = StatusBar("");
        self.search_text = "";
        self.app.bindings = {};
        self.app.unbind("ctrl+c");
        self.menu = MenuBar(self._editor_menus(), on_close=self._menu_closed);
        self.bar = FunctionBar([
            ("f1", "Help", self._editor_help),
            ("f2", "Symbols", self.symbol_map_dialog),
            ("f5", "Run/Stop", self.toggle_run),
            ("f6", "Window", self.switch_window),
            ("f9", "Menu", self.open_menu),
            ("f10", "Exit", self.quit),
        ]);
        self.bar.install(self.app);
        self.app.bind("ctrl+f9", self.run_buffer);
        self.app.bind("ctrl+f6", self.compile_buffer);
        self.app.bind("alt+f9", self.check_buffer);
        self.app.bind("ctrl+n", self.new_file);
        self.app.bind("ctrl+o", self.open_file_dialog);
        self.app.bind("ctrl+s", self.save);
        self.app.bind("ctrl+q", self.quit);
        self.app.bind("ctrl+x", self.editor.cut);
        self.app.bind("shift+delete", self.editor.cut);
        self.app.bind("ctrl+f", self.find_dialog);
        self.app.bind("f2", self.symbol_map_dialog);
        self.app.bind("alt+p", self.symbol_map_dialog);
        self.app.bind("f3", self.find_next);
        self.app.bind("shift+f3", self.find_previous);
        self.app.bind("ctrl+g", self.goto_line_dialog);
        self.app.bind("f5", self.toggle_run);
        self.app.bind("ctrl+r", self.toggle_run);
        self.app.bind("f6", self.switch_window);
        self.app.bind("ctrl+tab", self.switch_window);
        for key, index in (("alt+f", 0), ("alt+e", 1), ("alt+s", 2), ("alt+r", 3), ("alt+d", 4), ("alt+o", 5), ("alt+w", 6), ("alt+h", 7)):
            self.app.bind(key, lambda index=index: self.open_menu(index));
        self.app.bind("f11", self.toggle_window_maximize);
        self.app.bind("alt+enter", self.toggle_window_maximize);
        self.app.bind("alt+m", self.begin_window_move);
        self.app.bind("alt+z", self.begin_window_resize);
        self.app.bind("ctrl+f4", self.close_current_window);
        self.output_view = TextView("Ready. F5 runs the current buffer.");
        self.output_pane = TextViewPane(self.output_view);
        self.command_pane = CommandWindowPane(self.command);
        available_width = max(40, int(self.app.width));
        available_height = max(12, int(self.app.height) - 3);
        code_width = max(30, min(available_width - 2, int(available_width * 0.78)));
        code_height = max(9, min(available_height - 1, int(available_height * 0.72)));
        output_width = max(28, min(available_width - 4, int(available_width * 0.68)));
        output_height = max(7, min(available_height - 2, 10));
        command_width = max(28, min(available_width - 2, 44));
        command_height = max(7, min(available_height - 2, 11));
        self.code_window = WorkspaceWindow(self.editor, title="Code - {}".format(self.path.name), name="code", left=1, top=0, width=code_width, height=code_height, content_style="viewer");
        self.output_window = WorkspaceWindow(self.output_pane, title="Output", name="output", left=3, top=max(1, available_height - output_height), width=output_width, height=output_height, content_style="viewer");
        self.command_window = WorkspaceWindow(self.command_pane, title="Command", name="command", left=max(0, available_width - command_width - 1), top=max(1, available_height - command_height - 1), width=command_width, height=command_height, content_style="command");
        self.workspace = Workspace(
            self.output_window,
            self.command_window,
            self.code_window,
            layout_id="sumx",
            layout_path=self.config_path.with_name("workspaces.json"),
            viewport_width=available_width,
            viewport_height=available_height,
        );
        body = VBox(self.workspace, self.status, self.bar, sizes=[None, 1, 1]);
        self.desktop = MenuDesktop(self.menu, body);
        self.app.set_root(self.desktop);
        self.workspace.activate(self.code_window);
        self.menu.menus = self._editor_menus();
        self._update_editor_status();

    def _editor_menus(self):
        return [
            Menu("File", [
                MenuItem("New", self.new_file, "Ctrl+N"),
                MenuItem("Open...", self.open_file_dialog, "Ctrl+O"),
                MenuItem("Save", self.save, "Ctrl+S"),
                MenuItem("Save As...", self.save_as_dialog),
                Separator(),
                MenuItem("Compare with...", self.compare_with_dialog),
                Separator(),
                MenuItem("Exit", self.quit, "Ctrl+Q / F10"),
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
                MenuItem("Functions / Classes / Main...", self.symbol_map_dialog, "F2 / Alt+P"),
            ]),
            Menu("Run", [
                MenuItem("Check", self.check_buffer, "Alt+F9"),
                MenuItem("Run / Stop", self.toggle_run, "F5"),
                MenuItem("Compile to Python", self.compile_buffer, "Ctrl+F6"),
            ]),
            Menu("Debug", [
                MenuItem("Run to Cursor", enabled=False, shortcut="F4"),
                MenuItem("Trace Into", enabled=False, shortcut="F7"),
                MenuItem("Step Over", enabled=False, shortcut="F8"),
                MenuItem("Toggle Breakpoint", enabled=False),
                MenuItem("Reset", enabled=False, shortcut="Ctrl+F2"),
            ]),
            Menu("Options", [
                MenuItem("Theme", submenu=self._theme_menu()),
                Separator(),
                MenuItem("Show spaces", self.toggle_spaces, checked=lambda: self.editor.show_spaces),
                MenuItem("Show tabs", self.toggle_tabs, checked=lambda: self.editor.show_tabs),
                MenuItem("Show line endings", self.toggle_eols, checked=lambda: self.editor.show_line_endings),
                MenuItem("Show control characters", self.toggle_controls, checked=lambda: self.editor.show_control_chars),
                Separator(),
                MenuItem("Save configuration", self.save_configuration),
            ]),
            self._window_menu(),
            Menu("Help", [
                MenuItem("Context Help", self._editor_help, "F1"),
                MenuItem("sumX Help", self._help),
                MenuItem("Editor Keys", self._editor_keys_help),
                MenuItem("Configuration", self._configuration_help),
            ]),
        ];

    def open_menu(self, index=None):
        self.menu.menus = self._editor_menus();
        if index is None:
            index = self.menu.menu_index;
        self.menu.open(index);
        self.app.focus.set(self.menu);
        self.app.invalidate();
        return True;

    def _menu_closed(self):
        if hasattr(self, "workspace") and self.workspace.active_window is not None:
            focus = self.workspace.active_window.primary_focus();
            if focus is not None:
                self.app.focus.set(focus);
                self.app.invalidate();
                return True;
        self.app.focus.set(self.editor);
        self.app.invalidate();
        return True;

    def _set_document(self, document, path=None):
        self.document = document;
        if path is not None:
            self.path = Path(path).expanduser().resolve();
        if hasattr(self, "code_window"):
            self.code_window.title = "Code - {}".format(self.path.name);
            self.document.path = self.path;
        elif self.document.path is not None:
            self.path = Path(self.document.path).expanduser().resolve();
        self.editor.set_text(self.document.text, modified=False);
        self.app.focus.set(self.editor);
        self._update_editor_status("Loaded");
        return True;

    def _close_modal(self):
        if self.app.modal_depth:
            self.app.pop_modal();
        self.app.focus.set(self.editor);
        self.app.invalidate();
        return True;

    def _confirm_unsaved(self, callback):
        if not self.editor.modified:
            return callback();
        def cancel(*_args):
            return self._close_modal();
        def forget(*_args):
            self._close_modal();
            return callback();
        def save_then(*_args):
            self._close_modal();
            return self.save(on_saved=callback);
        body = VBox(
            Label("The current file has unsaved changes."),
            HBox(
                Button("SAVE_AND_EXIT", on_press=save_then, default=True, height=3),
                Button("FORGET_AND_EXIT", on_press=forget, height=3),
                Button("CANCEL", on_press=cancel, height=3),
                ratios=[1, 1, 1],
            ),
            sizes=[1, None],
        );
        self.app.push_modal(Dialog(body, title="Unsaved changes", width=76, height=9, on_cancel=cancel, shadow=True));
        self.app.invalidate();
        return True;

    def _new_file_now(self):
        target = Path.cwd() / "untitled.prg";
        return self._set_document(TextDocument.empty(target), target);

    def new_file(self):
        return self._confirm_unsaved(self._new_file_now);

    def open_file_dialog(self):
        start = self.path.parent if self.path is not None else Path.cwd();
        def close():
            self.app.pop_modal();
            self.app.focus.set(self.editor);
            self.app.invalidate();
        def accepted(path):
            selected = Path(path);
            close();
            def load_selected():
                try:
                    document = TextDocument.load(selected);
                    return self._set_document(document, selected);
                except Exception as exc:
                    self._update_editor_status("Open error: {}".format(exc));
                    return False;
            return self._confirm_unsaved(load_selected);
        dialog = FileDialog(path=start, title="Open sumX source", on_accept=accepted, on_cancel=close, theme=self.app.theme);
        self.app.push_modal(dialog);
        self.app.invalidate();
        return True;

    def save_as_dialog(self, on_saved=None):
        entry = TextInput(str(self.path));
        def close():
            self.app.pop_modal();
            self.app.focus.set(self.editor);
            self.app.invalidate();
        def accepted(*_args):
            self.path = Path(entry.value).expanduser().resolve();
            self.document.path = self.path;
            if hasattr(self, "code_window"):
                self.code_window.title = "Code - {}".format(self.path.name);
            close();
            return self.save(on_saved=on_saved);
        body = VBox(entry, HBox(Button("Save", on_press=accepted, default=True), Button("Cancel", on_press=close), ratios=[1, 1]), sizes=[1, None]);
        self.app.push_modal(Dialog(body, title="Save As", width=72, height=7, on_cancel=close));
        self.app.focus.set(entry);
        self.app.invalidate();
        return True;

    def compare_with_dialog(self):
        if not self.path.exists():
            return self.save(on_saved=self.compare_with_dialog);
        start = self.path.parent if self.path is not None else Path.cwd();
        def close(*_args):
            self._close_modal();
            return True;
        def accepted(path):
            selected = Path(path).expanduser().resolve();
            close();
            if selected == self.path.resolve():
                self._update_editor_status("Choose a different file to compare");
                return False;
            try:
                from sumtui.compare_integration import SumDiffUnavailable, launch_sumdiff;
                compare_app = launch_sumdiff(self.app, [self.path, selected], mode="compare", theme=self.app.theme.name, text_overrides={self.path: self.editor.text});
            except SumDiffUnavailable:
                self._update_editor_status("sumdiff is not installed; install sumdiff to use Compare");
                return False;
            except Exception as exc:
                self._update_editor_status("Compare error: {}".format(exc));
                return False;
            saved = {Path(item).expanduser().resolve() for item in getattr(compare_app, "saved_paths", set())};
            if self.path.resolve() in saved:
                try:
                    self._set_document(TextDocument.load(self.path), path=self.path);
                except Exception as exc:
                    self._update_editor_status("Compare reload error: {}".format(exc));
                    return False;
            self.menu.menus = self._editor_menus();
            self.app.focus.set(self.editor);
            self.app.invalidate();
            return True;
        dialog = FileDialog(path=start, title="Compare with file", on_accept=accepted, on_cancel=close, theme=self.app.theme);
        self.app.push_modal(dialog);
        self.app.invalidate();
        return True;

    def symbol_map(self):
        return build_symbol_map(self.editor.text, language="xbase", filename=self.path.name);

    def symbol_map_dialog(self):
        symbols = self.symbol_map();
        listing = ListView([(item.label, item) for item in symbols], title="Functions / Classes / Main");
        listing.select(symbol_index_for_line(symbols, self.editor.cursor_line));
        def close(*_args):
            self._close_modal();
            return True;
        def activate(*_args):
            item = listing.current_value;
            if item is None:
                return False;
            close();
            self.editor.goto_line(item.line, item.column);
            self.workspace.show(self.code_window);
            self._update_editor_status("{} {} - line {}".format(item.kind.upper(), item.name, item.line));
            return True;
        listing.on_activate = activate;
        body = VBox(listing, HBox(Button("Go", on_press=activate, default=True), Button("Cancel", on_press=close), ratios=[1, 1]), sizes=[None, None]);
        self.app.push_modal(Dialog(body, title="Program map", width=68, height=min(24, max(9, len(symbols) + 6)), on_cancel=close, shadow=True));
        self.app.focus.set(listing);
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
        body = VBox(entry, HBox(Button("Find", on_press=accepted, default=True), Button("Cancel", on_press=close), ratios=[1, 1]), sizes=[1, None]);
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
        body = VBox(entry, HBox(Button("Go", on_press=accepted, default=True), Button("Cancel", on_press=close), ratios=[1, 1]), sizes=[1, None]);
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
- **F1** contextual help; **F2** opens Program Map; **F5** toggles run/stop; **F6** cycles Code/Output/Command; **F11** maximizes/restores; **Ctrl+F4** closes the active window; **Ctrl+F6** compiles to Python.
- **Alt+M** enters keyboard Move and **Alt+Z** enters keyboard Resize; use arrows (Shift+arrows = five cells), Enter to accept and Escape to cancel. The lower-right window corner can also be dragged with the mouse to resize.
- **Ctrl+F9** runs the current buffer; **Alt+F9** checks it.
- **Ctrl+Z / Ctrl+Y** undo/redo.
- **Ctrl+C / Ctrl+X / Ctrl+V** copy/cut/paste. **Ctrl+S** saves, **Ctrl+O** opens and **Ctrl+Q** quits.
- **Shift+movement** extends selection.
- **Ctrl+Left / Ctrl+Right** move by words; add Shift to extend selection.
- **Ctrl+F**, **F3**, **Shift+F3** search; **Ctrl+G** goes to a line. **Alt+P** is an F2 alternative on keyboards without function keys.

The File/Edit/Search/Run/Debug/Options/Window/Help menus remain visible at the top. The Window menu can activate, close, or reopen the default Code/Output/Command windows.

Options also provides **Theme** and **Save configuration**. Saved editor visibility options and the chosen theme are restored on the next run.

Debug commands are placeholders until the debugger runtime is implemented.
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

    def save(self, on_saved=None):
        self.document.path = self.path;
        self.document.text = self.editor.text;
        try:
            self.document.save(text=self.editor.text);
            self.editor.mark_saved();
            self._update_editor_status("Saved");
            if on_saved is not None:
                return on_saved();
            return True;
        except Exception as exc:
            self._update_editor_status("Save error: {}".format(exc));
            return False;

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

    def switch_window(self):
        changed = self.workspace.next_window();
        if changed and self.workspace.active_window is not None:
            self._update_editor_status("Window: {}".format(self.workspace.active_window.title));
            self.app.invalidate();
        return bool(changed);

    def activate_window(self, window):
        changed = self.workspace.show(window);
        if changed:
            self._update_editor_status("Window: {}".format(window.title));
            self.app.invalidate();
        return bool(changed);

    def _close_current_window_now(self, target):
        changed = self.workspace.close(target);
        if changed:
            self._update_editor_status("Closed window: {}".format(target.title));
            self.app.invalidate();
        return bool(changed);

    def close_current_window(self, window=None):
        target = window or self.workspace.active_window;
        if target is None:
            return False;
        if target is self.code_window and self.editor.modified:
            return self._confirm_unsaved(lambda: self._close_current_window_now(target));
        return self._close_current_window_now(target);

    def _quit_now(self):
        self.app.stop();
        return True;

    def quit(self):
        return self._confirm_unsaved(self._quit_now);

    def run(self):
        self.workspace.load_layout();
        try:
            return self.app.run();
        finally:
            self.workspace.save_layout();

    def toggle_window_maximize(self, window=None):
        target = window or self.workspace.active_window;
        if target is None:
            return False;
        if self.workspace.active_window is not target:
            self.workspace.activate(target);
        changed = target.toggle_maximize();
        if changed:
            self._update_editor_status(("Maximized: " if target.maximized else "Restored: ") + target.title);
            self.app.invalidate();
        return bool(changed);

    def begin_window_move(self):
        if getattr(self, "workspace", None) is None or self.workspace.active_window is None:
            return False;
        changed = self.workspace.begin_move_active();
        if changed:
            self.app.invalidate();
        return bool(changed);

    def begin_window_resize(self):
        if getattr(self, "workspace", None) is None or self.workspace.active_window is None:
            return False;
        changed = self.workspace.begin_resize_active();
        if changed:
            self.app.invalidate();
        return bool(changed);

    def reset_window_layout(self):
        self.workspace.reset_layout(clear_saved=True);
        self._update_editor_status("Window layout restored to defaults");
        self.app.invalidate();
        return True;

    def _window_menu(self):
        items = [
            MenuItem("Next Window", self.switch_window, "F6 / Ctrl+Tab"),
            MenuItem("Maximize / Restore", self.toggle_window_maximize, "F11 / Alt+Enter", enabled=getattr(self, "workspace", None) is not None and self.workspace.active_window is not None),
            MenuItem("Move...", self.begin_window_move, "Alt+M", enabled=getattr(self, "workspace", None) is not None and self.workspace.active_window is not None and not self.workspace.active_window.maximized),
            MenuItem("Resize...", self.begin_window_resize, "Alt+Z", enabled=getattr(self, "workspace", None) is not None and self.workspace.active_window is not None and not self.workspace.active_window.maximized),
            MenuItem("Close current", self.close_current_window, "Ctrl+F4", enabled=getattr(self, "workspace", None) is not None and self.workspace.active_window is not None),
            MenuItem("Reset Window Layout", self.reset_window_layout),
            Separator(),
        ];
        workspace = getattr(self, "workspace", None);
        if workspace is not None:
            for window in workspace.windows:
                label = window.title + ("" if window.visible else " (closed)");
                entries = [];
                if window.visible:
                    entries.append(MenuItem("Activate", lambda selected=window: self.activate_window(selected), radio=lambda selected=window: workspace.active_window is selected));
                    entries.append(MenuItem("Restore" if window.maximized else "Maximize", lambda selected=window: self.toggle_window_maximize(selected), "F11 / Alt+Enter"));
                    entries.append(MenuItem("Close", lambda selected=window: self.close_current_window(selected)));
                else:
                    entries.append(MenuItem("Open", lambda selected=window: self.activate_window(selected)));
                items.append(MenuItem(label, submenu=Menu(label, entries), radio=lambda selected=window: workspace.active_window is selected));
        return Menu("Window", items);

    def _append_program_output(self, text):
        piece = str(text);
        if self.output_view.text == "Ready. F5 runs the current buffer.":
            self.output_view.set_text("");
        if piece and not piece.endswith("\n"):
            piece += "\n";
        self.output_view.append_text(piece);
        return True;

    def _handle_result(self, result):
        if isinstance(result, OutputResult) and self._program_active and result.emit:
            self._append_program_output(result.text);
            return None;
        return super()._handle_result(result);

    def _program_idle(self):
        if not self._program_active:
            self.app.remove_idle(self._program_idle);
            return False;
        if self._program_blocked:
            return False;
        self._continue_program();
        return True;

    def stop_buffer(self):
        if not self._program_active:
            self._update_editor_status("No program is running");
            return True;
        self._program_active = False;
        self._finish_program();
        self._update_editor_status("Run stopped");
        self.app.invalidate();
        return True;

    def toggle_run(self):
        return self.stop_buffer() if self._program_active else self.run_buffer();

    def run_buffer(self):
        if self._program_active:
            self.command.write_error("A program is already running");
            return False;
        self.output_view.set_text("--- Run {} ---".format(self.path.name));
        self.workspace.show(self.output_window);
        self._program_cooperative = True;
        self.app.add_idle(self._program_idle);
        self.run_program(self.editor.text, name=str(self.path));
        if self._program_active:
            self._update_editor_status("Running. F5 stops; F6 switches windows.");
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
        self.app.remove_idle(self._program_idle);
        self._program_cooperative = False;
        result = super()._finish_program();
        if hasattr(self, "editor"):
            self.app.focus.set(self.editor);
            self._update_editor_status("Run finished");
        return result;
