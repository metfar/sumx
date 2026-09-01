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
from rich.console import Console;
from rich.table import Table;
from pathlib import Path;
import subprocess;
import time;

from sumtui import message_color_scheme, Application, BrowseForm, Button, Column, CommandWindow, Dialog, FormField, FunctionBar, HBox, InputMask, Label, ListView, ListViewPane, MarkdownView, MarkdownViewPane, Menu, MenuBar, MenuDesktop, MenuItem, Panel, RecordForm, Separator, StatusBar, TableView, TextArea, TextInput, TextView, VBox;
from sumtui.clipboard import clipboard;

from . import __version__;
from .config import default_config_path, load_config, resolve_theme, save_config, theme_names;
from .helpdb import TOPICS, find_topic, index_markdown, topic_names;
from .interpreter import HELP_TEXT, Interpreter;
from .picture import picture_input_char;
from .results import AppendRequest, BatchResult, BrowseRequest, ClearResult, FormRequest, HelpRequest, InputRequest, OutputResult, QuitResult, ReadRequest, ScreenGetResult, ScreenWriteResult, TableResult, WindowRequest;
from .statements import needs_continuation, split_statements;


def _execute_shell_command(command):
    source = str(command).strip();
    if not source:
        raise ValueError("Shell command required after !");
    return subprocess.run(
        source,
        shell=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        check=False,
    );


def _shell_output_lines(completed):
    output = str(completed.stdout or "");
    lines = output.splitlines();
    if completed.returncode != 0:
        lines.append("[shell exit {}]".format(completed.returncode));
    return lines;


class SumXConsoleApp:
    def __init__(self, interpreter=None, database=":memory:", theme=None, config_path=None, config=None):
        self.interpreter = interpreter or Interpreter(database=database);
        self.config_path = Path(config_path).expanduser() if config_path is not None else default_config_path();
        self.config = dict(config) if isinstance(config, dict) else load_config(self.config_path);
        selected_theme = resolve_theme(theme, self.config);
        self.app = Application("sumX", theme=selected_theme, capture_control_keys=True, mouse=True);
        self.command = CommandWindow(prompt=". ", on_submit=self._submit);
        self.status = StatusBar(self.interpreter.runtime.db.status());
        self.interpreter.runtime.set_screen_size_provider(self._screen_size);
        self.interpreter.runtime.set_messagebox_handler(self._runtime_messagebox);
        self.continuation = [];
        self._program_statements = [];
        self._program_results = [];
        self._program_name = None;
        self._program_active = False;
        self._program_quit = False;
        self._program_blocked = False;
        self._program_cooperative = False;
        self._program_idle_budget = 8;
        self._window_widgets = {};
        self._active_window_name = None;
        self.command.write("sumX {} - xBase-inspired interpreter".format(__version__));
        self.command.write("HELP for commands. F9 menu. F10 exits.");
        self.menu = MenuBar(self._console_menus(), on_close=self._menu_closed);
        self.bar = FunctionBar([
            ("f1", "Help", self._help),
            ("f2", "Areas", self._areas),
            ("f5", "Browse", self._browse),
            ("f9", "Menu", self.open_menu),
            ("f10", "Exit", self.app.stop),
        ]);
        self.bar.install(self.app);
        self.app.bind("alt+f", lambda: self.open_menu(0));
        self.app.bind("alt+d", lambda: self.open_menu(1));
        self.app.bind("alt+o", lambda: self.open_menu(2));
        self.app.bind("alt+h", lambda: self.open_menu(3));
        body = VBox(Panel(self.command, title="sumX Command", content_style="command"), self.status, self.bar, sizes=[None, 1, 1]);
        self.desktop = MenuDesktop(self.menu, body);
        self.app.set_root(self.desktop);
        self.app.focus.set(self.command);

    def _runtime_messagebox(self, text, flags=0, title="Message"):
        previous_focus = self.app.focus.current;
        numeric_flags = int(flags or 0);
        low_flags = numeric_flags & 0x0F;
        icon_flags = numeric_flags & 0xF0;
        kind = {0x10: "error", 0x20: "question", 0x30: "warning", 0x40: "info"}.get(icon_flags, "info");
        color_scheme = message_color_scheme(self.app.theme, kind);
        buttons = [];
        state = {"value": 1};
        def close(value=1):
            state["value"] = int(value);
            self.app.pop_modal();
            if previous_focus is not None:
                self.app.focus.set(previous_focus);
            self.app.invalidate();
            return True;
        if low_flags == 4:
            buttons = [Button("Yes", on_press=lambda: close(6), default=True), Button("No", on_press=lambda: close(7))];
        elif low_flags == 1:
            buttons = [Button("OK", on_press=lambda: close(1), default=True), Button("Cancel", on_press=lambda: close(2))];
        else:
            buttons = [Button("OK", on_press=lambda: close(1), default=True)];
        message_style = "message_{}".format(kind);
        body = VBox(Label(str(text), style=message_style), HBox(*buttons, ratios=[1 for _item in buttons]), sizes=[None, None]);
        dialog = Dialog(body, title=str(title or "Message"), width=max(36, min(76, len(str(text)) + 8)), height=9, on_cancel=lambda: close(2), shadow=True, color_scheme=color_scheme, title_style=message_style);
        self.app.push_modal(dialog);
        self.app.focus.set(buttons[0]);
        self.app.invalidate();
        return 1;

    def _theme_menu(self):
        return Menu("Theme", [
            MenuItem(name, lambda selected=name: self.set_theme(selected), radio=lambda selected=name: self.app.theme.name.casefold() == selected.casefold())
            for name in theme_names()
        ]);

    def _console_menus(self):
        return [
            Menu("File", [
                MenuItem("Exit", self.app.stop, "F10"),
            ]),
            Menu("Database", [
                MenuItem("Work areas", self._areas, "F2"),
                MenuItem("Browse", self._browse, "F5"),
            ]),
            Menu("Options", [
                MenuItem("Theme", submenu=self._theme_menu()),
                Separator(),
                MenuItem("Save configuration", self.save_configuration),
            ]),
            Menu("Help", [
                MenuItem("sumX Help", self._help, "F1"),
                MenuItem("Configuration", self._configuration_help),
            ]),
        ];

    def set_theme(self, name):
        selected = resolve_theme(name, self.config);
        self.app.set_theme(selected);
        self.command.write("Theme -> {}".format(self.app.theme.name), style="command_info");
        self.app.invalidate();
        return True;

    def _configuration_snapshot(self):
        data = dict(self.config);
        data["theme"] = self.app.theme.name;
        if hasattr(self, "editor"):
            editor = dict(data.get("editor", {})) if isinstance(data.get("editor"), dict) else {};
            editor.update({
                "show_spaces": bool(self.editor.show_spaces),
                "show_tabs": bool(self.editor.show_tabs),
                "show_line_endings": bool(self.editor.show_line_endings),
                "show_control_chars": bool(self.editor.show_control_chars),
                "tab_size": int(self.editor.tab_size),
            });
            data["editor"] = editor;
        return data;

    def save_configuration(self):
        try:
            self.config = self._configuration_snapshot();
            target = save_config(self.config, self.config_path);
            message = "Configuration saved: {}".format(target);
            if hasattr(self, "editor"):
                self._update_editor_status(message);
            else:
                self.command.write(message, style="command_info");
            self.app.invalidate();
            return True;
        except Exception as exc:
            message = "Configuration error: {}".format(exc);
            if hasattr(self, "editor"):
                self._update_editor_status(message);
            else:
                self.command.write_error(message);
            self.app.invalidate();
            return False;

    def _configuration_help(self):
        text = """# sumX configuration

sumX can persist its interactive theme and editor display options.

## Theme

Open **Options > Theme** and choose any built-in or user theme discovered by sumTUI. `sumtheme` can clone/edit themes under the sumTUI user-theme directory, and those themes appear here on the next start.

Use **Options > Save configuration** to make the current selection persistent.

The default file is `~/.config/sumx/config.json`, or `$XDG_CONFIG_HOME/sumx/config.json` when XDG_CONFIG_HOME is set.

The command line can override the saved theme for one session:

```bash
sumx --theme "Ralesk's MC" programa.prg
sumx --theme DOS --run programa.prg
```

Use `sumx --list-themes` to list installed themes.

When compiling, sumX freezes the effective theme. Built-in themes are stored by name; custom/user themes are embedded as complete theme data in the generated Python so the target user does not need that theme installed.
""";
        self._show_help(text, title="sumX Configuration");
        return True;

    def open_menu(self, index=None):
        if index is None:
            index = self.menu.menu_index;
        self.menu.open(index);
        self.app.focus.set(self.menu);
        self.app.invalidate();
        return True;

    def _menu_closed(self):
        self.app.focus.set(self.command);
        self.app.invalidate();
        return True;

    def _screen_size(self):
        if self.command.viewport_width > 1 and self.command.viewport_height > 1:
            return self.command.viewport_width, self.command.viewport_height;
        size = self.app.console.size;
        return max(1, int(size.width) - 2), max(1, int(size.height) - 5);

    def _update_status(self):
        self.status.set(self.interpreter.runtime.db.status());
        self.app.invalidate();

    def _help(self):
        self._show_help(index_markdown());

    def _areas(self):
        self._handle_result(self.interpreter.execute("DISPLAY WORKAREAS"));

    def _browse(self):
        try:
            self._handle_result(self.interpreter.execute("BROWSE"));
        except Exception as exc:
            self.command.write_error(str(exc));
        self._update_status();

    def _run_shell(self, command):
        try:
            completed = _execute_shell_command(command);
        except Exception as exc:
            self.command.write_error("Shell error: {}".format(exc));
            self.app.invalidate();
            return None;
        for line in _shell_output_lines(completed):
            style = "command_error" if line.startswith("[shell exit ") else "command";
            self.command.write(line, style=style);
        self.app.invalidate();
        return completed.returncode;

    def _submit(self, line, window):
        text = str(line);
        stripped = text.lstrip();
        if not self.continuation and stripped.startswith("!"):
            self._run_shell(stripped[1:]);
            self._update_status();
            return None;
        if self.continuation:
            self.continuation.append(text);
            text = "\n".join(self.continuation);
        if needs_continuation(text, line_continuation=self.interpreter.runtime.line_continuation, ampersand_comment=self.interpreter.runtime.ampersand_comment):
            if not self.continuation:
                self.continuation = [str(line)];
            window.set_prompt(".. ");
            return None;
        self.continuation = [];
        window.set_prompt(". ");
        try:
            result = self.interpreter.execute(text, interactive=True);
            self._handle_result(result);
        except Exception as exc:
            self.command.write_error("Error: {}".format(exc));
        self._update_status();
        return None;

    @property
    def program_active(self):
        return bool(self._program_active);

    @property
    def program_requested_quit(self):
        return bool(self._program_quit);

    def run_program(self, source, name="<program>"):
        if self._program_active:
            raise RuntimeError("A sumX program is already running");
        self._program_statements = list(split_statements(
            source,
            line_continuation=self.interpreter.runtime.line_continuation,
            ampersand_comment=self.interpreter.runtime.ampersand_comment,
        ));
        self._program_statements = self.interpreter.prepare_statements(self._program_statements);
        self._program_results = [];
        self._program_name = str(name);
        self._program_active = True;
        self._program_quit = False;
        self._program_blocked = False;
        self._continue_program();
        return self;

    def run_program_file(self, path):
        path = Path(path);
        source = path.read_text(encoding="utf-8", errors="replace");
        return self.run_program(source, name=str(path));

    def _finish_program(self):
        while self._active_window_name is not None:
            self._close_window(self._active_window_name, release=False);
        self.command.commit_screen_to_history();
        self._program_statements = [];
        self._program_results = [];
        self._program_name = None;
        self._program_active = False;
        self._program_blocked = False;
        self._update_status();
        return None;

    def _resume_program(self):
        self._program_blocked = False;
        return self._continue_program();

    def _handle_program_result(self, result):
        if result is None:
            return False;
        if isinstance(result, BatchResult):
            self._program_results = list(result.results) + self._program_results;
            return False;
        if isinstance(result, HelpRequest):
            self._program_blocked = True;
            self._show_help(result.text, title=result.title, after_close=self._resume_program);
            return True;
        if isinstance(result, BrowseRequest):
            self._program_blocked = True;
            self._show_browse(result, after_close=self._resume_program);
            return True;
        if isinstance(result, TableResult):
            self._program_blocked = True;
            self._show_table(result, after_close=self._resume_program);
            return True;
        if isinstance(result, AppendRequest):
            self._program_blocked = True;
            self._show_record_form(result.table, result.columns, result.title, after_close=self._resume_program);
            return True;
        if isinstance(result, FormRequest):
            self._program_blocked = True;
            self._show_record_form(result.table, result.columns, result.title, after_close=self._resume_program);
            return True;
        if isinstance(result, InputRequest):
            self._program_blocked = True;
            self._show_input(result, after_done=self._resume_program);
            return True;
        if isinstance(result, ReadRequest):
            self._program_blocked = True;
            self._begin_read(result, after_done=self._resume_program);
            return True;
        if isinstance(result, QuitResult):
            self._program_quit = True;
            self._finish_program();
            self.app.stop();
            return True;
        self._handle_result(result);
        return False;

    def _continue_program(self):
        if not self._program_active:
            return None;
        if self._program_blocked:
            if self.app.modal_depth == 0 and not bool(getattr(self.command, "read_active", False)):
                self._program_blocked = False;
            else:
                return None;
        budget = self._program_idle_budget if self._program_cooperative else None;
        steps = 0;
        try:
            while self._program_active and not self._program_blocked:
                if budget is not None and steps >= budget:
                    return None;
                steps += 1;
                if self._program_results:
                    result = self._program_results.pop(0);
                elif self._program_statements:
                    statement = str(self._program_statements[0]).strip();
                    parsed_if = self.interpreter._parse_if_statement(statement);
                    if parsed_if is not None:
                        condition, tail, single_line = parsed_if;
                        if single_line:
                            if bool(self.interpreter.evaluate(condition)):
                                self._program_statements[0] = tail;
                            else:
                                self._program_statements.pop(0);
                            continue;
                        else_index, endif_index = self.interpreter._find_if_block(self._program_statements, 0);
                        selected = bool(self.interpreter.evaluate(condition));
                        if selected:
                            branch_end = else_index if else_index is not None else endif_index;
                            branch = self._program_statements[1:branch_end];
                        else:
                            branch = self._program_statements[else_index + 1:endif_index] if else_index is not None else [];
                        self._program_statements[:endif_index + 1] = branch;
                        continue;
                    if statement.upper() in ("ELSE", "ENDIF"):
                        raise RuntimeError("Unexpected {}".format(statement.upper()));
                    self._program_statements.pop(0);
                    result = self.interpreter.execute(statement, interactive=True);
                else:
                    self._finish_program();
                    return None;
                if isinstance(result, BatchResult):
                    self._program_results = list(result.results) + self._program_results;
                    continue;
                blocked = self._handle_program_result(result);
                self._update_status();
                if blocked:
                    return None;
        except Exception as exc:
            name = self._program_name or "<program>";
            self._program_error = exc;
            if hasattr(self, "_program_exit_code"):
                self._program_exit_code = 1;
            self.command.write_error("Error in {}: {}".format(name, exc));
            self._finish_program();
        return None;

    def _window_command(self, name=None):
        key = str(name or self._active_window_name or "").casefold();
        item = self._window_widgets.get(key);
        return item[1] if item is not None else None;

    def _open_window(self, request):
        definition = dict(request.definition or {});
        name = str(request.name);
        key = name.casefold();
        if self._active_window_name is not None and self._active_window_name.casefold() != key:
            raise RuntimeError("Only one active DEFINE WINDOW is supported at a time");
        existing = self._window_widgets.get(key);
        if existing is not None:
            dialog, child = existing;
        else:
            child = CommandWindow(prompt="", show_prompt=False, theme=self.app.theme, content_style=None);
            dialog = Dialog(
                child,
                title=str(definition.get("title") or name),
                width=max(12, int(definition.get("width", 40))),
                height=max(5, int(definition.get("height", 10))),
                padding=(0, 0),
                on_cancel=lambda: self._close_window(name, release=False),
                top=definition.get("top"),
                left=definition.get("left"),
                shadow=bool(definition.get("shadow", False)),
                panel=bool(definition.get("panel", False)),
                color_scheme=definition.get("color_scheme"),
            );
            self._window_widgets[key] = (dialog, child);
        self.app.push_modal(dialog);
        self._active_window_name = name;
        self.app.focus.set(child);
        self.app.invalidate();
        return child;

    def _close_window(self, name, release=False):
        key = str(name).casefold();
        item = self._window_widgets.get(key);
        if item is None:
            self._active_window_name = None;
            return False;
        _dialog, child = item;
        if self._active_window_name is not None and self._active_window_name.casefold() == key:
            if self.app._modal_stack:
                self.app.pop_modal();
            self._active_window_name = None;
            self.app.focus.set(self.command);
        if release:
            self._window_widgets.pop(key, None);
        self.app.invalidate();
        return True;

    def _handle_window_request(self, request):
        action = str(request.action).lower();
        if action == "activate":
            self._open_window(request);
            return True;
        if action == "deactivate":
            return self._close_window(request.name, release=False);
        if action == "release":
            return self._close_window(request.name, release=True);
        return False;

    def _handle_result(self, result):
        if result is None:
            return;
        if isinstance(result, BatchResult):
            for item in result.results:
                self._handle_result(item);
            return;
        if isinstance(result, OutputResult):
            if not result.emit:
                return;
            self.command.write(result.text, style="command_info" if result.level != "OUTPUT" else "command");
        elif isinstance(result, WindowRequest):
            self._handle_window_request(result);
        elif isinstance(result, ScreenWriteResult):
            target = self._window_command(result.window) if result.window else self.command;
            if target is None:
                target = self.command;
            target.write_at(result.row, result.column, result.text, style=result.style);
            self.app.invalidate();
        elif isinstance(result, ScreenGetResult):
            field = result.field;
            target = self._window_command(field.window) if field.window else self.command;
            if target is None:
                target = self.command;
            target.define_field(
                field.target, field.row, field.column, field.width, field.value, fixed=field.fixed,
                height=field.height, max_length=field.max_length, multiline=field.height > 1,
                picture=field.picture, overflow=field.overflow,
            );
            self.app.invalidate();
        elif isinstance(result, InputRequest):
            self._show_input(result);
        elif isinstance(result, ReadRequest):
            self._begin_read(result);
        elif isinstance(result, ClearResult):
            self.command.clear();
        elif isinstance(result, QuitResult):
            self.app.stop();
        elif isinstance(result, HelpRequest):
            self._show_help(result.text, title=result.title);
        elif isinstance(result, BrowseRequest):
            self._show_browse(result);
        elif isinstance(result, TableResult):
            self._show_table(result);
        elif isinstance(result, AppendRequest):
            self._show_record_form(result.table, result.columns, result.title);
        elif isinstance(result, FormRequest):
            self._show_record_form(result.table, result.columns, result.title);

    def _show_input(self, request, after_done=None):
        picture = InputMask.parse(request.picture) if request.picture else None;
        overflow = bool(self.interpreter.runtime.field_wrap_overflow);
        timeout_callback = {"value": None};
        status = Label("");

        def current_value():
            return entry.value if hasattr(entry, "value") else entry.text;

        def close():
            if timeout_callback["value"] is not None:
                self.app.remove_idle(timeout_callback["value"]);
                timeout_callback["value"] = None;
            self.app.pop_modal();
            self.app.focus.set(self.command);
            self.app.invalidate();

        def shown_value(raw):
            raw = str(raw or "");
            if request.hidden:
                return "";
            if request.mask is not None:
                return str(request.mask) * len(raw);
            if picture is not None:
                return picture.format(raw, overflow=overflow).rstrip();
            return raw;

        def accept(value=None, timed_out=False):
            entered = current_value() if value is None else str(value);
            if entered == "" and request.default_character:
                entered = str(request.default_character);
            try:
                self.interpreter.apply_input_value(request, entered);
                close();
                suffix = shown_value(entered);
                timeout_note = " [timeout]" if timed_out else "";
                self.command.write("{}{}{}".format(request.prompt, suffix, timeout_note), style="command");
                self._update_status();
                if request.remaining:
                    self._handle_result(self.interpreter.execute_remaining(request.remaining, interactive=True));
                if after_done is not None:
                    after_done();
            except Exception as exc:
                close();
                self.command.write_error("{} error: {}".format(request.command, exc));
                self.app.invalidate();
            return True;

        def cancel():
            close();
            self.command.write("{} cancelled".format(request.command), style="command_info");
            if self._program_active:
                self._finish_program();
            self.app.invalidate();
            return True;

        if request.height > 1:
            entry = TextArea("", line_numbers=False, tab_moves_focus=True);
            entry_height = max(1, int(request.height));
        else:
            char_filter = None;
            maximum = None;
            display_transform = None;
            display_cursor = None;
            clear_on_edit = False;
            if request.keys:
                maximum = 1;
                def char_filter(_position, char):
                    valid = request.keys if request.case_sensitive else request.keys.upper();
                    probe = char if request.case_sensitive else char.upper();
                    return char if probe in valid else None;
            elif picture is not None:
                maximum = None if overflow else picture.capacity;
                char_filter = lambda position, char: picture.input_char(position, char, overflow=overflow);
                display_transform = lambda value: picture.format(value, overflow=overflow);
                display_cursor = lambda value, position: picture.cursor_display_position(value, position, overflow=overflow);
                clear_on_edit = picture.clear_on_edit;
            field_width = None if request.width is None else max(3, int(request.width) + 2);
            entry = TextInput(
                "", width=field_width, max_length=maximum, echo_mask=request.mask,
                hidden=request.hidden, char_filter=char_filter, display_transform=display_transform,
                display_cursor=display_cursor, clear_on_first_edit=clear_on_edit,
                confirm_at_limit=self.interpreter.runtime.confirm,
            );
            entry_height = 1;
            entry.on_submit = lambda value: accept(value);
            if request.keys:
                entry.on_change = lambda value: accept(value) if value else None;

        buttons = HBox(Button("OK", on_press=lambda: accept(), default=True), Button("Cancel", on_press=cancel), ratios=[1, 1]);
        body = VBox(Label(str(request.prompt)), entry, status, buttons, sizes=[1, entry_height, 1, 1]);
        width_hint = request.width or max(30, len(str(request.prompt)));
        dialog = Dialog(body, title="{} -> {}".format(request.command, request.target), width=max(36, min(96, int(width_hint) + 10)), height=max(8, entry_height + 7), on_cancel=cancel);
        self.app.push_modal(dialog);
        self.app.focus.set(entry);

        if request.timeout_seconds is not None:
            deadline = time.monotonic() + max(0.0, float(request.timeout_seconds));
            previous_second = {"value": None};
            def tick():
                remaining = max(0.0, deadline - time.monotonic());
                second = int(remaining + 0.999);
                dirty = second != previous_second["value"];
                if dirty:
                    previous_second["value"] = second;
                    default_text = " default={}".format(request.default_character) if request.default_character else "";
                    status.set_text("Timeout: {}s{}".format(second, default_text));
                if remaining <= 0.0:
                    accept(request.default_character, timed_out=True);
                    return True;
                return dirty;
            timeout_callback["value"] = tick;
            self.app.add_idle(tick);

        self.app.invalidate();
        return True;

    def _begin_read(self, request, after_done=None):
        window_names = {str(field.window).casefold() for field in request.fields if getattr(field, "window", None)};
        if len(window_names) > 1:
            raise RuntimeError("READ cannot currently span more than one DEFINE WINDOW");
        target_command = self.command;
        if window_names:
            target_command = self._window_command(next(iter(window_names)));
            if target_command is None:
                raise RuntimeError("READ target window is not active");
        fields = [];
        for field in request.fields:
            char_filter = None;
            if field.picture:
                char_filter = lambda position, char, picture=field.picture, overflow=field.overflow: picture_input_char(picture, position, char, overflow=overflow);
            fields.append({
                "name": field.target,
                "row": field.row,
                "column": field.column,
                "width": field.width,
                "value": field.value,
                "fixed": field.fixed,
                "height": field.height,
                "max_length": field.max_length,
                "multiline": field.height > 1,
                "picture": field.picture,
                "overflow": field.overflow,
                "char_filter": char_filter,
                "validator": (lambda value, source=field: self.interpreter.validate_get_field(source, value)),
                "validation_error": str(field.error or ""),
            });

        def accept(values, _widget):
            try:
                self.interpreter.apply_read_values(request.fields, values);
                if target_command is self.command:
                    self.command.commit_screen_to_history();
                self._update_status();
                if request.remaining:
                    self._handle_result(self.interpreter.execute_remaining(request.remaining, interactive=True));
                if after_done is not None:
                    after_done();
            except Exception as exc:
                self.command.write_error("READ error: {}".format(exc));
                self.app.invalidate();

        def cancel(_values, _widget):
            if target_command is self.command:
                self.command.commit_screen_to_history();
            self.command.write("READ cancelled", style="command_info");
            self.app.invalidate();
            if after_done is not None:
                after_done();

        def validation_error(_field, message, _widget):
            if str(message or ""):
                self._runtime_messagebox(str(message), 48, "Validation");
            self.app.invalidate();
            return True;

        if target_command is self.command and hasattr(self, "workspace") and hasattr(self, "command_window"):
            self.workspace.activate(self.command_window);
        if not target_command.begin_read(
            fields, on_accept=accept, on_cancel=cancel, confirm=self.interpreter.runtime.confirm,
            on_validation_error=validation_error,
        ):
            self.command.write_error("READ: no fields");
        self.app.focus.set(target_command);
        self.app.invalidate();

    def _show_help(self, text, title="sumX Help", after_close=None):
        current = {"topic": None};
        viewer = MarkdownView(str(text));
        names = topic_names();

        def show_topic(value, _row=None):
            topic = find_topic(value);
            if topic is None:
                return False;
            current["topic"] = topic;
            viewer.set_text(topic.markdown());
            self.app.invalidate();
            return True;

        topics = ListView([(name, name) for name in names], title="Topics", on_change=show_topic, on_activate=show_topic);
        requested = None;
        if " - " in str(title):
            requested = find_topic(str(title).split(" - ", 1)[1]);
        if requested is not None:
            for index, name in enumerate(names):
                if name == requested.name:
                    topics.select(index);
                    current["topic"] = requested;
                    viewer.set_text(requested.markdown());
                    break;

        def close():
            self.app.pop_modal();
            self._update_status();
            if after_close is not None:
                after_close();

        def search():
            def find(value):
                needle = str(value).strip().casefold();
                if not needle:
                    return False;
                for index, name in enumerate(names):
                    topic = TOPICS.get(name.upper());
                    haystack = "{} {} {}".format(name, topic.category if topic else "", topic.summary if topic else "").casefold();
                    if needle in haystack:
                        topics.select(index);
                        show_topic(name);
                        self.app.focus.set(topics);
                        return True;
                return False;
            self._show_search(find, title="Help Search");

        def copy_example():
            topic = current.get("topic");
            if topic is None:
                copied = viewer.copy_code_block(-1);
                if not copied:
                    clipboard.copy_text(viewer.markdown);
                    hints.set("Help text copied");
                else:
                    hints.set("Code example copied");
            else:
                clipboard.copy_text(topic.example);
                hints.set("Example copied: {}".format(topic.name));
            self.app.invalidate();
            return True;

        def run_example():
            topic = current.get("topic");
            if topic is None:
                return False;
            example = topic.example;
            close();
            if example.lstrip().startswith("!"):
                self._run_shell(example.lstrip()[1:]);
                return True;
            if not self._program_active:
                self.run_program(example, name="<help:{}>".format(topic.name));
            return True;

        def topic_map():
            rows = [];
            current_index = 0;
            current_topic = current.get("topic");
            for index, name in enumerate(names):
                topic = find_topic(name);
                category = getattr(topic, "category", "") if topic is not None else "";
                rows.append(("{} / {}".format(category, name) if category else name, name));
                if current_topic is not None and name == current_topic.name:
                    current_index = index;
            listing = ListView(rows, title="Category / Topic");
            listing.select(current_index);

            def map_close():
                self.app.pop_modal();
                self.app.focus.set(topics);
                self.app.invalidate();
                return True;

            def map_activate(*_values):
                name = listing.current_value;
                if name is None:
                    return False;
                for index, topic_name in enumerate(names):
                    if topic_name == name:
                        topics.select(index);
                        break;
                show_topic(name);
                return map_close();

            listing.on_activate = map_activate;
            pane = ListViewPane(listing, theme=self.app.theme);
            status = StatusBar("Enter Go to topic  Esc Return to help");
            self.app.push_modal(Dialog(VBox(pane, status, sizes=[None, 1]), title="sumX Help Topic Map", width=72, height=min(28, max(12, len(rows) + 6)), on_cancel=map_close, shadow=True));
            self.app.focus.set(listing);
            self.app.invalidate();
            return True;

        hints = StatusBar("F2 Topic Map  Tab Topic/Text  F3 Search  F5 Run Example  F6/Ctrl+C Copy Example  F11 Max/Restore  Esc Close");
        topics_pane = ListViewPane(topics, theme=self.app.theme);
        viewer_pane = MarkdownViewPane(view=viewer, theme=self.app.theme);
        body = HBox(topics_pane, viewer_pane, sizes=[28, None]);
        content = VBox(body, hints, sizes=[None, 1]);
        dialog = Dialog(content, title=title, width=104, height=30, on_cancel=close, padding=(0, 1), maximizable=True);
        self.app.push_modal(dialog, bindings={"f2": topic_map, "f3": search, "f5": run_example, "f6": copy_example, "ctrl+c": copy_example});
        self.app.focus.set(topics);

    def _show_search(self, on_find, title="Search"):
        status = StatusBar("Type text to search; Enter finds next match");
        field = None;

        def close():
            self.app.pop_modal();
            self.app.invalidate();

        def find(value):
            try:
                if on_find(value):
                    close();
                    return;
                status.set("Not found: {}".format(value));
                self.app.invalidate();
            except Exception as exc:
                status.set("Search error: {}".format(exc));
                self.app.invalidate();

        field = TextInput("", placeholder="Search...", width=44, on_submit=find);
        buttons = HBox(Button("Find", on_press=lambda: find(field.value), default=True), Button("Cancel", on_press=close));
        content = VBox(HBox(Label("Find:"), field, sizes=[8, None]), buttons, status, sizes=[1, 1, 1]);
        dialog = Dialog(content, title=title, width=60, height=7, on_cancel=close, padding=(0, 1));
        self.app.push_modal(dialog);
        self.app.focus.set(field);

    def _show_table(self, result, after_close=None):
        columns = [Column(str(name)) for name in result.columns];
        table = TableView(columns);
        table.set_rows([(list(row), index) for index, row in enumerate(result.rows)]);

        def close():
            self.app.pop_modal();
            self._update_status();
            if after_close is not None:
                after_close();

        dialog = Dialog(table, title=result.title, width=min(110, max(50, 12 * max(1, len(columns)))), height=20, on_cancel=close, padding=(0, 1), maximizable=True);
        self.app.push_modal(dialog);

    @staticmethod
    def _column_mask(column):
        logical = str(column.logical_type or "").upper();
        declared = str(column.declared_type or logical).upper();
        if column.autoinum:
            return "<auto>";
        if logical in ("CHARACTER", "VARCHAR"):
            width = min(48, max(1, int(column.length or 20)));
            return "X" * width;
        if logical in ("MEMO", "TEXT"):
            return "X" * 48;
        if logical == "NUMERIC":
            precision = max(1, int(column.precision or 10));
            scale = max(0, int(column.scale or 0));
            integer_digits = max(1, precision - scale);
            mask = ("9" * max(0, integer_digits - 1)) + "0";
            if scale:
                mask += "." + ("0" * scale);
            return mask;
        if logical == "INTEGER":
            return "9999999990";
        if logical == "FLOAT":
            return "9999990.00";
        if logical == "DATE":
            return "99/99/9999";
        if logical == "TIME":
            return "99:99:99";
        if logical == "DATETIME":
            return "9999-99-99 99:99:99";
        if logical == "UUID":
            return "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX";
        if logical == "JSON":
            return "{...}";
        if logical == "BLOB":
            return "<file path>";
        if declared in ("LOGICAL", "BOOL", "BOOLEAN", "L"):
            return "L";
        return "X" * 20;

    @staticmethod
    def _column_initial(column):
        if column.autoinum:
            return "<auto>";
        if column.default_sql is None:
            return False if column.logical_type == "LOGICAL" else "";
        raw = str(column.default_sql);
        if column.logical_type == "LOGICAL":
            return raw.strip().upper() in ("1", "TRUE", ".T.", "ON");
        if column.logical_type == "NUMERIC":
            try:
                return column.display(int(raw));
            except Exception:
                return raw;
        return raw.strip().strip('"').strip("'");

    def _field_for_column(self, column):
        mask = self._column_mask(column);
        logical = str(column.logical_type or "").upper();
        if column.autoinum:
            width = max(8, len(mask));
            return FormField(column.name, value="<auto>", width=width, readonly=True);
        if logical == "LOGICAL":
            return FormField(column.name, value=self._column_initial(column), width=1, kind="logical", mask="L");
        if logical in ("CHARACTER", "VARCHAR"):
            width = min(48, max(6, int(column.length or 20)));
        elif logical in ("MEMO", "TEXT", "BLOB", "JSON"):
            width = 48;
        else:
            width = min(48, max(8, len(mask)));
        max_length = column.length;
        if max_length is None and logical in ("NUMERIC", "INTEGER", "FLOAT", "DATE", "TIME", "DATETIME", "UUID"):
            max_length = max(width, len(mask));
        placeholder = "file path" if logical == "BLOB" else "";
        return FormField(
            column.name,
            value=self._column_initial(column),
            width=width,
            max_length=max_length,
            kind="text",
            mask=mask,
            placeholder=placeholder,
        );

    def _show_browse(self, result, after_close=None):
        columns = [Column(str(name)) for name in result.columns];
        prepared = [(list(row), index) for index, row in enumerate(result.rows)];
        browser = None;

        def changed(value, _row):
            if result.table and self.interpreter.runtime.db.current_area.table == result.table:
                try:
                    self.interpreter.runtime.db.current_area.recno = int(value) + 1;
                except (TypeError, ValueError):
                    pass;
                self._update_status();

        def refresh_browser():
            if not result.table:
                return;
            try:
                _columns, rows = self.interpreter.runtime.db.browse(table=result.table, limit=max(200, len(browser.table.rows) or 1));
                browser.set_rows([(list(row), index) for index, row in enumerate(rows)]);
                if rows and self.interpreter.runtime.db.current_area.table == result.table:
                    browser.select(max(0, min(len(rows) - 1, self.interpreter.runtime.db.recno() - 1)));
                self.app.invalidate();
            except Exception as exc:
                self.command.write_error("Browse refresh error: {}".format(exc));

        def edit_current(*_args):
            if result.readonly or not result.table or not browser.table.rows:
                return False;
            recno = browser.selected + 1;
            self.interpreter.runtime.db.current_area.recno = recno;
            self._show_record_form(
                result.table,
                self.interpreter.runtime.db.columns(result.table),
                "Edit: {}".format(result.table),
                after_close=refresh_browser,
                record_number=recno,
                append=False,
            );
            return True;

        def new_record(*_args):
            if result.readonly or not result.table:
                return False;
            self._show_record_form(
                result.table,
                self.interpreter.runtime.db.columns(result.table),
                "New*: {}".format(result.table),
                after_close=refresh_browser,
                record_number=None,
                append=True,
            );
            return True;

        browser = BrowseForm(columns, prepared, on_change=changed, on_activate=edit_current);
        if result.table and self.interpreter.runtime.db.current_area.table == result.table and result.rows:
            browser.select(max(0, min(len(result.rows) - 1, self.interpreter.runtime.db.recno() - 1)));

        def search():
            self._show_search(lambda value: browser.find(value), title="Search: {}".format(result.table or result.title));

        def close():
            self.app.pop_modal();
            self._update_status();
            if after_close is not None:
                after_close();

        buttons = HBox(
            Button("First", on_press=browser.first),
            Button("Prev", on_press=browser.previous),
            Button("Next", on_press=browser.next),
            Button("Last", on_press=browser.last),
            Button("Search", on_press=search),
            Button("New*", on_press=new_record, enabled=not result.readonly and bool(result.table)),
            Button("Edit", on_press=edit_current, enabled=not result.readonly and bool(result.table)),
            Button("Exit", on_press=close),
        );
        hints = StatusBar("Enter Edit  New* Append  Arrows/PgUp/PgDn Browse  F11 Max/Restore  Esc Exit");
        content = VBox(browser, buttons, hints, sizes=[None, 1, 1]);
        widths = [];
        for index, column in enumerate(result.columns):
            sample = [len(str(row[index])) for row in result.rows[:50] if index < len(row)];
            widths.append(min(24, max([len(str(column)), 4] + sample)));
        dialog_width = min(120, max(72, sum(widths) + (3 * len(widths)) + 4));
        dialog = Dialog(content, title=result.title, width=dialog_width, height=24, on_cancel=close, padding=(0, 1), maximizable=True);
        self.app.push_modal(dialog);

    def _show_record_form(self, table, columns, title, after_close=None, record_number=None, append=True):
        fields = [self._field_for_column(column) for column in columns];
        form = RecordForm(fields);
        defaults = {field.name: field.value for field in fields};
        state = {"mode": "append" if append and record_number is None else "edit", "recno": int(record_number or 0)};

        def display_record_values(values):
            prepared = {};
            for column in columns:
                value = values.get(column.name, "");
                if isinstance(value, (bytes, bytearray)):
                    value = "<{} bytes>".format(len(value));
                prepared[column.name] = value;
            form.set_values(prepared);

        def load_record(number):
            count = self.interpreter.runtime.db.reccount_for(table);
            if count <= 0:
                return False;
            number = max(1, min(count, int(number)));
            values = self.interpreter.runtime.db.record_at(number, table=table);
            if not values:
                return False;
            state["mode"] = "edit";
            state["recno"] = number;
            if self.interpreter.runtime.db.current_area.table == table:
                self.interpreter.runtime.db.current_area.recno = number;
            display_record_values(values);
            record_status.set("Record {}/{}  EDIT".format(number, count));
            self._update_status();
            self.app.invalidate();
            return True;

        def reset():
            if state["mode"] == "edit" and state["recno"]:
                load_record(state["recno"]);
            else:
                form.set_values(defaults);
                record_status.set("New record  APPEND");
                self.app.invalidate();

        def collect_values():
            values = {};
            raw_values = form.values();
            for col in columns:
                if col.autoinum:
                    continue;
                value = raw_values.get(col.name);
                if isinstance(value, str):
                    if value == "":
                        value = None;
                    elif col.logical_type == "BLOB":
                        if value.startswith("<") and value.endswith(" bytes>") and state["mode"] == "edit":
                            continue;
                        value = Path(value).expanduser().read_bytes();
                if value is not None:
                    values[col.name] = value;
            return values;

        def finish():
            self.app.pop_modal();
            self._update_status();
            if after_close is not None:
                after_close();

        def save(close_after=False):
            try:
                values = collect_values();
                if state["mode"] == "append":
                    rowid = self.interpreter.runtime.db.append(values, table=table);
                    state["recno"] = self.interpreter.runtime.db.reccount_for(table);
                    state["mode"] = "edit";
                    if self.interpreter.runtime.debug_enabled("INFO"):
                        self.command.write("Record appended to {} (rowid {})".format(table, rowid), style="command_info");
                else:
                    self.interpreter.runtime.db.update_record(values, recno=state["recno"], table=table);
                    if self.interpreter.runtime.debug_enabled("INFO"):
                        self.command.write("Record {} updated in {}".format(state["recno"], table), style="command_info");
                load_record(state["recno"]);
                self._update_status();
                if close_after:
                    finish();
            except Exception as exc:
                self.command.write_error("Record error: {}".format(exc));
                self.app.invalidate();

        def goto_first():
            return load_record(1);

        def goto_prev():
            current = state["recno"] or self.interpreter.runtime.db.recno() or 1;
            return load_record(current - 1);

        def goto_next():
            current = state["recno"] or self.interpreter.runtime.db.recno() or 0;
            return load_record(current + 1);

        def goto_last():
            return load_record(self.interpreter.runtime.db.reccount_for(table));

        def search():
            def find(value):
                start = state["recno"] or 0;
                found = self.interpreter.runtime.db.find_record(value, table=table, start_recno=start);
                return load_record(found) if found else False;
            self._show_search(find, title="Search: {}".format(table));

        record_status = StatusBar("New record  APPEND" if state["mode"] == "append" else "Record {}  EDIT".format(state["recno"]));
        if state["mode"] == "edit" and state["recno"]:
            load_record(state["recno"]);
        else:
            form.set_values(defaults);

        buttons = HBox(
            Button("First", on_press=goto_first),
            Button("Prev", on_press=goto_prev),
            Button("Next", on_press=goto_next),
            Button("Last", on_press=goto_last),
            Button("Search", on_press=search),
            Button("Ok", on_press=lambda: save(False), default=True),
            Button("Cancel", on_press=reset),
            Button("Exit", on_press=finish),
        );
        hints = StatusBar("Enter/Tab Next  Up PrevField  Ctrl+End Save+Exit  Esc Exit  F11 Max/Restore");
        content = VBox(form, record_status, buttons, hints, sizes=[None, 1, 1, 1]);
        field_count = max(1, len(fields));
        max_field_width = max([field.width for field in fields] or [20]);
        label_width = max([len(field.label or field.name) + 2 for field in fields] or [10]);
        width = min(120, max(84, label_width + max_field_width + 10));
        height = min(34, max(11, field_count + 8));
        dialog = Dialog(content, title=title, width=width, height=height, on_cancel=finish, maximizable=True);
        self.app.push_modal(dialog, bindings={"ctrl+end": lambda: save(True)});

    def run(self):
        return self.app.run();


class SumXProgramApp(SumXConsoleApp):
    """Run a .PRG with the full interactive sumTUI runtime but no assistant.

    This mode is intentionally distinct from the command window and the IDE:
    programs still receive DEFINE WINDOW, GET/READ, INPUT DIALOG, BROWSE,
    APPEND and FORM services, while no development menus or command prompt are
    shown unless the program explicitly requests them in a future extension.
    """
    def __init__(self, interpreter=None, database=":memory:", theme=None, config_path=None, config=None):
        super().__init__(interpreter=interpreter, database=database, theme=theme, config_path=config_path, config=config);
        self.command.clear();
        self.command.show_prompt = False;
        self.command.on_submit = None;
        self._program_exit_code = 0;
        self._program_error = None;
        self._scheduled_program = None;
        self._started_program = False;
        self.app.bindings = {};
        self.app.bind("ctrl+c", self._cancel_program);
        self.app.bind("f10", self._cancel_program);
        self.app.set_root(self.command);
        self.app.focus.set(self.command);

    def _cancel_program(self):
        self._program_exit_code = 130;
        self._program_active = False;
        self.app.stop();
        return True;

    def _finish_program(self):
        super()._finish_program();
        self.app.stop();
        return None;

    def _start_scheduled_program(self):
        if self._started_program:
            return False;
        self._started_program = True;
        self.app.remove_idle(self._start_scheduled_program);
        try:
            self.run_program_file(self._scheduled_program);
        except Exception as exc:
            self._program_error = exc;
            self._program_exit_code = 1;
            self.command.write_error("Error in {}: {}".format(self._scheduled_program, exc));
            self.app.stop();
        return True;

    def history_lines(self):
        return list(self.command.output);

    def run_file(self, path):
        self._scheduled_program = str(path);
        self._started_program = False;
        self.app.add_idle(self._start_scheduled_program);
        self.app.run();
        return self._program_exit_code;


def print_result(console, result, error_console=None):
    if result is None:
        return;
    if isinstance(result, BatchResult):
        for item in result.results:
            print_result(console, item, error_console=error_console);
        return;
    if isinstance(result, OutputResult):
        if not result.emit:
            return;
        target = error_console if result.channel == "stderr" and error_console is not None else console;
        target.print(result.text);
    elif isinstance(result, HelpRequest):
        console.print(result.text);
    elif isinstance(result, ScreenWriteResult):
        if result.window:
            console.print(result.text);
            return;
        stream = getattr(console, "file", None);
        is_tty = bool(stream is not None and hasattr(stream, "isatty") and stream.isatty());
        if is_tty:
            stream.write("\x1b[{};{}H{}".format(result.row + 1, result.column + 1, result.text));
            stream.flush();
        else:
            console.print(result.text);
    elif isinstance(result, (ScreenGetResult, ReadRequest, InputRequest)):
        return;
    elif isinstance(result, ClearResult):
        console.clear();
    elif isinstance(result, (BrowseRequest, TableResult)):
        table = Table(title=result.title);
        for column in result.columns:
            table.add_column(str(column));
        for row in result.rows:
            table.add_row(*[str(value) for value in row]);
        console.print(table);


def plain_repl(interpreter):
    console = Console();
    diagnostics = Console(stderr=True);
    console.print("sumX {} - HELP for commands".format(__version__));
    continuation = [];
    while True:
        prompt = ".. " if continuation else ". ";
        try:
            line = input(prompt);
        except (EOFError, KeyboardInterrupt):
            console.print();
            return 0;
        stripped = line.lstrip();
        if not continuation and stripped.startswith("!"):
            try:
                completed = _execute_shell_command(stripped[1:]);
                for output_line in _shell_output_lines(completed):
                    target = diagnostics if output_line.startswith("[shell exit ") else console;
                    target.print(output_line);
            except Exception as exc:
                diagnostics.print("Shell error: {}".format(exc), style="bold red");
            continue;
        text = "\n".join(continuation + [line]) if continuation else line;
        if needs_continuation(text, line_continuation=interpreter.runtime.line_continuation, ampersand_comment=interpreter.runtime.ampersand_comment):
            continuation.append(line);
            continue;
        continuation = [];
        try:
            result = interpreter.execute(text, interactive=True);
            batch = result.results if isinstance(result, BatchResult) else [result];
            for item in batch:
                if isinstance(item, QuitResult):
                    return 0;
                if isinstance(item, (AppendRequest, FormRequest)):
                    values = {};
                    for col in item.columns:
                        if col.autoinum:
                            continue;
                        value = input("{} [{}]: ".format(col.name, col.declared_type));
                        if value != "":
                            values[col.name] = value;
                    rowid = interpreter.runtime.db.append(values, table=item.table);
                    if interpreter.runtime.debug_enabled("INFO"):
                        diagnostics.print("Record appended (rowid {})".format(rowid));
                elif isinstance(item, InputRequest):
                    entered = input(str(item.prompt));
                    interpreter.apply_input_value(item, entered);
                    if item.remaining:
                        print_result(console, interpreter.execute_remaining(item.remaining, interactive=True), error_console=diagnostics);
                elif isinstance(item, ReadRequest):
                    values = {};
                    for field in item.fields:
                        entered = input("{} [{}]: ".format(field.target, field.value.rstrip()));
                        values[field.target] = entered if entered != "" else field.value;
                    interpreter.apply_read_values(item.fields, values);
                    if item.remaining:
                        print_result(console, interpreter.execute_remaining(item.remaining, interactive=True), error_console=diagnostics);
                elif isinstance(item, ScreenGetResult):
                    continue;
                else:
                    print_result(console, item, error_console=diagnostics);
        except Exception as exc:
            diagnostics.print("Error: {}".format(exc), style="bold red");
