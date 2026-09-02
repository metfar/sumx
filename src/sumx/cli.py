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
import argparse;
from pathlib import Path;
import sys;

from rich.console import Console;
from sumui import add_backend_arguments, backend_from_args;

from sumtui import InputSpec, read_input;

from . import __version__;
from .compiler import check_source, compile_file;
from .config import load_config, resolve_theme, theme_names;
from .console import SumXConsoleApp, SumXProgramApp, plain_repl, print_result;
from .editor_app import SumXEditorApp;
from .interpreter import Interpreter;
from .results import AppendRequest, BatchResult, FormRequest, InputRequest, ReadRequest, QuitResult;


def self_test():
    interp = Interpreter();
    stored = interp.execute("STORE 5 TO A");
    assert stored.text == "A = 5" and stored.emit is False;
    assert interp.evaluate("a = 5 AND ON") is True;
    assert interp.evaluate("OFF") is False;
    assert interp.evaluate("ON && ~OFF") is True;
    assert interp.evaluate("ON || OFF") is True;
    assert interp.evaluate("ON ^^ OFF") is True;
    info = interp.execute("SET DEBUG_LEVEL INFO");
    assert info.emit is True and interp.runtime.debug_level == "INFO";
    interp.execute("SET DEBUG_LEVEL OFF");
    interp.execute("SET CAPS_SENSITIVE ON");
    interp.execute("CaseName=1");
    interp.execute("casename=2");
    assert interp.evaluate("CaseName") == 1;
    assert interp.evaluate("casename") == 2;
    interp = Interpreter();
    interp.execute("CREATE TABLE t (id AUTONUM, name VARCHAR(20), memo MEMO, amount CURRENCY, active LOGICAL)");
    interp.execute("USE t AS testalias");
    interp.execute('APPEND name="Alice", amount=12.34, active=ON');
    result = interp.execute("BROW");
    assert result.rows[0][1] == "Alice";
    assert result.rows[0][3] == "12.3400";
    interp.execute("CHANNEL 0");
    assert interp.runtime.db.active_area == 2;
    interp.execute("SEL testalias");
    assert interp.runtime.db.active_area == 1;
    interp.execute("N=SQL.SELECT count(*) FROM t");
    assert interp.evaluate("N") == 1;
    interp.execute("C=SQL.SELECT id,name FROM t INTO CURSOR rows");
    assert len(interp.runtime.get_value("rows")) == 1;
    interp.execute('O=OBJ(name="Alice", tags=[1,2])');
    assert interp.evaluate("O.name") == "Alice";
    assert interp.evaluate("O.tags[1]") == 2;
    batch = interp.execute("X=1; Y=2; ? X+Y; # three statements");
    assert batch.results[-1].text == "3";
    screen = interp.execute('@5,5 SAY "hello"');
    assert screen.row == 5 and screen.column == 5 and screen.text == "hello";
    assert interp.evaluate("SPACE(3)") == "   ";
    assert interp.evaluate('REPLICATE("x",3)') == "xxx";
    interp.execute("nom=SPACE(8)");
    pair = interp.execute('@2,1 SAY "Name:" GET nom');
    assert isinstance(pair, BatchResult);
    read = interp.execute("READ");
    assert isinstance(read, ReadRequest) and read.fields[0].width == 8;
    interp.apply_read_values(read.fields, {"nom": "Ana".ljust(8)});
    assert interp.evaluate("nom") == "Ana".ljust(8);
    assert interp.execute('PRINT 1250.50 PICTURE "$999,999.99"').text == "$  1,250.50";
    assert interp.evaluate('TRANSFORM("usuario12","@! NNNNNNNN")') == "USUARIO1";
    interp.execute("SET FIELD_WRAP_OVERFLOW ON");
    assert interp.evaluate('TRANSFORM("usuario12","@! NNNNNNNN")') == "USUARIO12";
    interp.runtime.set_screen_size_provider(lambda: (101, 37));
    assert interp.evaluate("WCOLS()") == 101 and interp.evaluate("WROWS()") == 37;
    accept = interp.execute('ACCEPT "Name: " TO cName;');
    assert accept.command == "ACCEPT" and accept.text_only is True;
    interp.apply_input_value(accept, "Ada");
    assert interp.evaluate("cName") == "Ada";
    continued = interp.execute(
        'INPUT "Continue?" answer \\\n'
        ' KEYS "YN" \\\n'
        ' DEFAULT "N" \\\n'
        ' DIALOG ;'
    );
    assert continued.keys == "YN" and continued.default_character == "N" and continued.dialog is True;
    conditional = interp.execute('IF 5==5 THEN PRINT "IF OK"');
    assert conditional.text == "IF OK";
    interp.execute("SET AMPERSAND_COMMENT ON\nA=7 && comment");
    assert interp.evaluate("A") == 7;
    interp.execute("SET AMPERSAND_COMMENT OFF");
    interp.runtime.db.close();
    print("sumX {} self-test: OK".format(__version__));
    return 0;


def _process_file_results(interpreter, console, diagnostics, results, plain=False):
    queue = list(results);
    while queue:
        result = queue.pop(0);
        if isinstance(result, BatchResult):
            queue = list(result.results) + queue;
            continue;
        if isinstance(result, (AppendRequest, FormRequest)):
            if not sys.stdin.isatty():
                raise RuntimeError("{} requires an interactive terminal in file mode".format("APPEND" if isinstance(result, AppendRequest) else "FORM"));
            values = {};
            for col in result.columns:
                if col.autoinum:
                    continue;
                entered = input("{} [{}]: ".format(col.name, col.declared_type));
                if entered != "":
                    values[col.name] = entered;
            interpreter.runtime.db.append(values, table=result.table);
            continue;
        if isinstance(result, InputRequest):
            spec = InputSpec(
                prompt=result.prompt,
                width=result.width,
                height=result.height,
                picture=result.picture,
                overflow=interpreter.runtime.field_wrap_overflow,
                hidden=result.hidden,
                mask=result.mask,
                keys=result.keys,
                case_sensitive=result.case_sensitive,
                default=result.default_character,
                timeout=result.timeout_seconds,
                dialog=(False if plain else result.dialog),
                title="{} -> {}".format(result.command, result.target),
            );
            response = read_input(spec);
            if response.status == 1:
                raise RuntimeError("{} cancelled".format(result.command));
            interpreter.apply_input_value(result, response.value);
            if result.remaining:
                continuation = interpreter.execute_remaining(result.remaining, interactive=False);
                if continuation is not None:
                    queue.insert(0, continuation);
            continue;
        if isinstance(result, ReadRequest):
            if not sys.stdin.isatty():
                raise RuntimeError("READ requires an interactive terminal in file mode");
            values = {};
            for field in result.fields:
                entered = input("{} [{}]: ".format(field.target, field.value.rstrip()));
                values[field.target] = entered if entered != "" else field.value;
            interpreter.apply_read_values(result.fields, values);
            if result.remaining:
                continuation = interpreter.execute_remaining(result.remaining, interactive=False);
                if continuation is not None:
                    queue.insert(0, continuation);
            continue;
        print_result(console, result, error_console=diagnostics);
    return 0;


def main(argv=None):
    parser = argparse.ArgumentParser(prog="sumx", description="sumX - educational xBase-inspired language environment");
    parser.add_argument("file", nargs="?", help="open a .prg file in the sumX editor");
    parser.add_argument("-c", "--command", help="execute one or more statements and exit");
    actions = parser.add_mutually_exclusive_group();
    actions.add_argument("--run", metavar="FILE", help="execute a .prg with the interactive sumTUI runtime, without opening the IDE");
    actions.add_argument("--compile", dest="compile_program", metavar="FILE", help="generate readable executable Python that uses the sumX runtime");
    actions.add_argument("--check", metavar="FILE", help="check source structure without executing it");
    parser.add_argument("-o", "--output", help="output file for --compile; use - for stdout");
    parser.add_argument("--database", default=":memory:", help="SQLite database path (default: in-memory)");
    parser.add_argument("--plain", action="store_true", help="force plain textual terminal I/O and disable Sum UI widgets");
    add_backend_arguments(parser);
    parser.add_argument("--console", action="store_true", help="open the classic command-only sumX frontend instead of the common sumIDE xBase workspace");
    parser.add_argument("--theme", default=None, help="sumTUI theme for this interactive session; saved configuration is used when omitted");
    parser.add_argument("--config", help="configuration file path (default: XDG_CONFIG_HOME/sumx/config.json or ~/.config/sumx/config.json)");
    parser.add_argument("--list-themes", action="store_true", help="list available sumTUI themes and exit");
    parser.add_argument("--debug-level", default="OFF", choices=["off", "info", "debug", "trace"], type=str.lower, help="diagnostic verbosity; default: off");
    parser.add_argument("--line-continuation", choices=["backslash", "semicolon"], default="backslash", help="physical-line continuation style; default: backslash");
    parser.add_argument("--ampersand-comment", action="store_true", help="treat && as an xBase inline comment instead of logical AND");
    parser.add_argument("--version", action="store_true", help="show version and exit");
    parser.add_argument("--self-test", action="store_true", help="run non-interactive self-test");
    args = parser.parse_args(argv);
    ui_backend = backend_from_args(args);
    if args.plain and ui_backend == "gui":
        parser.error("--plain and --gui are mutually exclusive");
    if args.version:
        print("sumX {}".format(__version__));
        return 0;
    if args.list_themes:
        print("\n".join(theme_names()));
        return 0;
    if args.self_test:
        return self_test();
    config = load_config(args.config);
    selected_theme = resolve_theme(args.theme, config);
    if args.output and not args.compile_program:
        parser.error("--output requires --compile");
    if args.file and (args.run or args.compile_program or args.check or args.command is not None or args.console):
        parser.error("a positional .prg file opens the editor; use it separately from --run/--compile/--check/--command");
    if args.compile_program:
        try:
            generated, output = compile_file(
                args.compile_program,
                output=args.output,
                line_continuation=args.line_continuation.upper(),
                ampersand_comment=args.ampersand_comment,
                theme=selected_theme,
            );
            if args.output == "-":
                sys.stdout.write(generated);
                if not generated.endswith("\n"):
                    sys.stdout.write("\n");
            else:
                print("Compiled {} -> {}".format(args.compile_program, output));
            return 0;
        except Exception as exc:
            print("Compile error: {}".format(exc), file=sys.stderr);
            return 1;
    if args.check:
        try:
            source = Path(args.check).read_text(encoding="utf-8", errors="replace");
            statements = check_source(
                source,
                line_continuation=args.line_continuation.upper(),
                ampersand_comment=args.ampersand_comment,
            );
            print("Check OK: {} statement(s)".format(len(statements)));
            return 0;
        except Exception as exc:
            print("Check error: {}".format(exc), file=sys.stderr);
            return 1;
    interpreter = Interpreter(database=args.database);
    interpreter.runtime.set_debug_level(args.debug_level);
    interpreter.runtime.set_line_continuation(args.line_continuation.upper());
    interpreter.runtime.set_ampersand_comment(args.ampersand_comment);
    console = Console();
    diagnostics = Console(stderr=True);
    if args.command is not None:
        try:
            result = interpreter.execute(args.command, interactive=False);
            print_result(console, result, error_console=diagnostics);
            return 0;
        except Exception as exc:
            diagnostics.print("Error: {}".format(exc), style="bold red");
            return 1;
    if args.run:
        try:
            if args.plain or not sys.stdin.isatty() or not sys.stdout.isatty():
                results = interpreter.run_file(args.run, interactive=False);
                return _process_file_results(interpreter, console, diagnostics, results, plain=True);
            runner = SumXProgramApp(interpreter=interpreter, theme=selected_theme, config_path=args.config, config=config);
            code = runner.run_file(args.run, backend=ui_backend);
            for line, style in runner.history_lines():
                target = diagnostics if style == "command_error" else console;
                target.print(line);
            return code;
        except Exception as exc:
            diagnostics.print("Error: {}".format(exc), style="bold red");
            return 1;
    if args.file:
        if args.plain or (ui_backend == "tui" and (not sys.stdin.isatty() or not sys.stdout.isatty())):
            diagnostics.print("Opening a source file in TUI mode requires an interactive terminal. Use --gui or --run.", style="bold red");
            return 2;
        try:
            return SumXEditorApp(args.file, interpreter=interpreter, theme=args.theme, config_path=args.config).run(backend=ui_backend);
        except Exception as exc:
            diagnostics.print("Error: {}".format(exc), style="bold red");
            return 1;
    if args.plain or (ui_backend == "tui" and (not sys.stdin.isatty() or not sys.stdout.isatty())):
        return plain_repl(interpreter);
    if args.console:
        return SumXConsoleApp(interpreter=interpreter, theme=selected_theme, config_path=args.config, config=config).run(backend=ui_backend);
    try:
        ide = SumXEditorApp(None, interpreter=interpreter, theme=args.theme, config_path=args.config);
        ide.activate_workspace_window(ide.command_window);
        ide._update_status("xBase Command - File manages source programs");
        return ide.run(backend=ui_backend);
    except Exception as exc:
        diagnostics.print("Error: {}".format(exc), style="bold red");
        return 1;


if __name__ == "__main__":
    raise SystemExit(main());
