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
"""sumX language backend for the common sumIDE shell.

The historical sumX editor donated its language/runtime integration to this
small adapter.  Windows, editing, preferences, templates and multi-language
source management are owned by :mod:`sumide`.
""";
from pathlib import Path;

from sumide.app import ScriptIDE;

from .compiler import check_source, compile_source;
from .console import SumXConsoleApp;
from .interpreter import Interpreter;
from .results import OutputResult;


class SumXEditorApp(ScriptIDE, SumXConsoleApp):
    """Common sumIDE shell with a stateful, cooperative xBase backend.""";
    def __init__(self, path=None, interpreter=None, database=":memory:", theme=None, config_path=None, config=None, **kwargs):
        self.interpreter = interpreter or Interpreter(database=database);
        self.continuation = [];
        self._program_statements = [];
        self._program_results = [];
        self._program_name = None;
        self._program_active = False;
        self._program_quit = False;
        self._program_blocked = False;
        self._program_delay_deadline = None;
        self._program_cooperative = False;
        self._program_idle_budget = 8;
        self._window_widgets = {};
        self._active_window_name = None;
        if config_path is not None and "sumide_config_path" not in kwargs:
            kwargs["sumide_config_path"] = config_path;
        del config;
        super().__init__(path=path, language="xbase", theme=theme, **kwargs);
        self.app.title = "sumX";
        self.command = self.command_view;
        self.command.on_submit = self._submit_xbase;
        self.path = Path(self.document.path).expanduser().resolve() if self.document.path is not None else Path("Untitled.prg");
        self.interpreter.runtime.set_screen_size_provider(self._screen_size);
        self.interpreter.runtime.set_messagebox_handler(self._runtime_messagebox);
        self.output_view.set_text("Ready. F5 runs the current xBase buffer.");
        self._update_status("xBase IDE");

    @property
    def program_active(self):
        return bool(self._program_active);

    @property
    def program_requested_quit(self):
        return bool(self._program_quit);

    def _submit_xbase(self, line, window):
        return SumXConsoleApp._submit(self, line, window);

    def _append_program_output(self, text):
        piece = str(text);
        if self.output_view.text.startswith("Ready."):
            self.output_view.set_text("");
        if piece and not piece.endswith("\n"):
            piece += "\n";
        self.output_view.append_text(piece);
        return True;

    def _handle_result(self, result):
        if isinstance(result, OutputResult) and self._program_active and result.emit:
            self._append_program_output(result.text);
            return None;
        return SumXConsoleApp._handle_result(self, result);

    def _program_idle(self):
        if not self._program_active:
            self.app.remove_idle(self._program_idle);
            return False;
        if self._program_blocked:
            return False;
        SumXConsoleApp._continue_program(self);
        return True;

    def run_buffer(self):
        if self._program_active:
            self.command.write_error("A program is already running");
            return False;
        name = str(self.document.path or self.path);
        self.output_view.set_text("--- Run {} ---\n".format(Path(name).name));
        self.workspace.show(self.output_window);
        self.workspace.activate(self.output_window);
        self._program_cooperative = True;
        self.app.add_idle(self._program_idle);
        SumXConsoleApp.run_program(self, self.editor.text, name=name);
        if self._program_active:
            self._update_status("Running xBase. F5 stops; F6 switches windows.");
        self.app.invalidate();
        return True;

    def run_program(self):
        return self.run_buffer();

    def stop_buffer(self):
        if not self._program_active:
            self._update_status("No xBase program is running");
            return True;
        self._program_active = False;
        self._finish_program();
        self._update_status("Run stopped");
        self.app.invalidate();
        return True;

    def stop_program(self):
        return self.stop_buffer();

    def toggle_run(self):
        return self.stop_buffer() if self._program_active else self.run_buffer();

    def _finish_program(self):
        self.app.remove_idle(self._program_idle);
        self._program_cooperative = False;
        result = SumXConsoleApp._finish_program(self);
        if hasattr(self, "editor"):
            self.app.focus.set(self.editor);
            self._update_status("Run finished");
        return result;

    def check_buffer(self):
        try:
            statements = check_source(
                self.editor.text,
                line_continuation=self.interpreter.runtime.line_continuation,
                ampersand_comment=self.interpreter.runtime.ampersand_comment,
            );
            self.command.write("Check OK: {} statement(s)".format(len(statements)), style="command_info");
            self._update_status("Check complete");
            return True;
        except Exception as exc:
            self.command.write_error("Check error: {}".format(exc));
            self._update_status("Check failed");
            return False;

    def compile_buffer(self):
        try:
            source_name = str(self.document.path or self.path);
            generated = compile_source(
                self.editor.text,
                source_name=source_name,
                line_continuation=self.interpreter.runtime.line_continuation,
                ampersand_comment=self.interpreter.runtime.ampersand_comment,
                theme=self.app.theme.name,
            );
            source_path = Path(self.document.path) if self.document.path is not None else self.path;
            output = source_path.with_suffix(".py");
            output.write_text(generated, encoding="utf-8");
            try:
                output.chmod(output.stat().st_mode | 0o111);
            except OSError:
                pass;
            self.command.write("Compiled -> {}".format(output), style="command_info");
            self._update_status("Compiled");
            return True;
        except Exception as exc:
            self.command.write_error("Compile error: {}".format(exc));
            self._update_status("Compile failed");
            return False;

    def compile_program(self):
        return self.compile_buffer();

    # Public compatibility names retained while callers migrate to sumIDE.
    def _editor_menus(self):
        return self._menus();

    def save_configuration(self):
        return self.save_config();

    def close_current_window(self, window=None):
        return self.close_workspace_window(window);

    def activate_window(self, window):
        return self.activate_workspace_window(window);

    def toggle_window_maximize(self, window=None):
        return self.toggle_workspace_maximize(window);

    def _quit_now(self):
        try:
            self.interpreter.runtime.db.close();
        except Exception:
            pass;
        return ScriptIDE._quit_now(self);
