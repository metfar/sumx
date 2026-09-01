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
import tempfile;
import unittest;
from types import SimpleNamespace;
from unittest.mock import patch;
from pathlib import Path;

from sumtui import Key, KeyEvent, ListView;
from sumx import Interpreter, SumCursor, SumObject, SumQuery, SumRow;
from sumx.compiler import compile_file, compile_source;
from sumx.helpdb import TOPICS, find_topic;
from sumx.console import SumXConsoleApp, SumXProgramApp;
from sumx.editor_app import SumXEditorApp;
from sumx.results import AppendRequest, BatchResult, BrowseRequest, FormRequest, HelpRequest, OutputResult, ReadRequest, ScreenGetResult, ScreenWriteResult, TableResult;
from sumx.statements import needs_continuation, split_statements;


class EditorMenuTests(unittest.TestCase):
    def test_editor_has_full_top_menu_and_f9_f10(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "menu.prg";
            path.write_text('PRINT "hello"\n', encoding="utf-8");
            app = SumXEditorApp(path);
            try:
                self.assertEqual([menu.title for menu in app.menu.menus], ["File", "Edit", "Search", "View", "Options", "Window", "Run", "Help"]);
                self.assertIn("f9", app.app.bindings);
                self.assertIn("f10", app.app.bindings);
                self.assertIn("alt+i", app.app.bindings);
                self.assertNotIn("alt+w", app.app.bindings);
                self.assertFalse(app.menu.mnemonics);
                self.assertTrue(app.open_menu(0));
                self.assertIs(app.app.focus.current, app.menu);
                self.assertTrue(app.menu.active);
                app.menu.close();
                self.assertIs(app.app.focus.current, app.editor);
            finally:
                app.interpreter.runtime.db.close();

    def test_editor_f5_run_stop_f6_window_and_ctrl_f6_compile(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "keys.prg";
            path.write_text('PRINT "hello"\n', encoding="utf-8");
            app = SumXEditorApp(path);
            try:
                self.assertIn("f5", app.app.bindings);
                self.assertIn("f6", app.app.bindings);
                self.assertIn("ctrl+f6", app.app.bindings);
                app.app.focus.set(app.editor);
                self.assertTrue(app.app.dispatch(KeyEvent(Key.F6)));
                self.assertIs(app.app.focus.current, app.output_view);
                self.assertTrue(app.app.dispatch(KeyEvent(Key.F6)));
                self.assertIs(app.app.focus.current, app.command);
                self.assertTrue(app.app.dispatch(KeyEvent(Key.F6)));
                self.assertIs(app.app.focus.current, app.editor);
                app._program_active = True;
                self.assertTrue(app.toggle_run());
                self.assertFalse(app._program_active);
            finally:
                app.interpreter.runtime.db.close();

    def test_editor_run_is_cooperative_so_f5_can_stop_between_statement_batches(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "longrun.prg";
            source = "\n".join('PRINT "line {}"'.format(index) for index in range(40));
            path.write_text(source + "\n", encoding="utf-8");
            app = SumXEditorApp(path);
            try:
                self.assertTrue(app.run_buffer());
                self.assertTrue(app.program_active);
                self.assertTrue(app.app.dispatch(KeyEvent(Key.F5)));
                self.assertFalse(app.program_active);
            finally:
                app.interpreter.runtime.db.close();




    def test_editor_read_activates_command_and_overwrites_default_picture_value(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "read.prg";
            path.write_text('answer = "N"\n@ 3, 2 GET answer WIDTH 1 PICTURE "@! A"\nREAD\nPRINT "Respuesta: " + answer\n', encoding="utf-8");
            app = SumXEditorApp(path);
            try:
                self.assertTrue(app.run_buffer());
                self.assertTrue(app.command.read_active);
                self.assertIs(app.workspace.active_window, app.command_window);
                self.assertIs(app.app.focus.current, app.command);
                self.assertTrue(app.app.dispatch(KeyEvent("y", text="y")));
                self.assertEqual(app.command.read_values()["answer"], "Y");
                self.assertTrue(app.app.dispatch(KeyEvent(Key.ENTER)));
                self.assertFalse(app.program_active);
                self.assertIn("Respuesta: Y", app.output_view.text);
            finally:
                app.interpreter.runtime.db.close();

    def test_editor_confirm_on_keeps_bounded_get_active_and_replaces_last_character_repeatedly(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "confirm_on.prg";
            path.write_text(
                'answer = "N"\n'
                'SET CONFIRM ON\n'
                '@ 3, 2 GET answer WIDTH 1 PICTURE "@! A"\n'
                'READ\n'
                'PRINT "Respuesta: " + answer\n',
                encoding="utf-8",
            );
            app = SumXEditorApp(path);
            try:
                self.assertTrue(app.run_buffer());
                self.assertTrue(app.command.read_active);
                for char in "YES":
                    self.assertTrue(app.app.dispatch(KeyEvent(char.lower(), text=char)));
                    self.assertTrue(app.command.read_active);
                self.assertEqual(app.command.read_values()["answer"], "S");
                self.assertTrue(app.app.dispatch(KeyEvent(Key.ENTER)));
                self.assertFalse(app.program_active);
                self.assertIn("Respuesta: S", app.output_view.text);
            finally:
                app.interpreter.runtime.db.close();

    def test_editor_confirm_off_auto_advances_and_accepts_final_get(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "confirm_off.prg";
            path.write_text(
                'first = ""\n'
                'second = ""\n'
                'SET CONFIRM OFF\n'
                '@ 1, 1 GET first WIDTH 1 PICTURE "X"\n'
                '@ 2, 1 GET second WIDTH 1 PICTURE "X"\n'
                'READ\n'
                'PRINT first + second\n',
                encoding="utf-8",
            );
            app = SumXEditorApp(path);
            try:
                self.assertTrue(app.run_buffer());
                self.assertTrue(app.command.read_active);
                self.assertTrue(app.app.dispatch(KeyEvent("y", text="Y")));
                self.assertTrue(app.command.read_active);
                self.assertEqual(app.command.read_index, 1);
                self.assertTrue(app.app.dispatch(KeyEvent("n", text="N")));
                self.assertFalse(app.command.read_active);
                self.assertFalse(app.program_active);
                self.assertIn("YN", app.output_view.text);
            finally:
                app.interpreter.runtime.db.close();

    def test_editor_named_window_read_accepts_input_and_closes_cleanly(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "window.prg";
            path.write_text(
                'answer = "N"\n'
                'DEFINE WINDOW wDialogo FROM 4, 10 TO 12, 55 TITLE " Confirmación " SHADOW PANEL COLOR SCHEME 5\n'
                'ACTIVATE WINDOW wDialogo\n'
                '@ 1, 2 PRINT "¿Desea continuar?"\n'
                '@ 3, 2 GET answer WIDTH 1 PICTURE "@! A"\n'
                'READ\n'
                'DEACTIVATE WINDOW wDialogo\n'
                'RELEASE WINDOW wDialogo\n'
                'PRINT "Respuesta: " + answer\n',
                encoding="utf-8",
            );
            app = SumXEditorApp(path);
            try:
                self.assertTrue(app.run_buffer());
                child = app._window_command("wDialogo");
                self.assertIsNotNone(child);
                self.assertIsNone(child.content_style);
                self.assertTrue(child.read_active);
                self.assertEqual(app.app.modal_depth, 1);
                for char in "YES":
                    self.assertTrue(app.app.dispatch(KeyEvent(char.lower(), text=char)));
                    self.assertTrue(child.read_active);
                self.assertEqual(child.read_values()["answer"], "S");
                self.assertTrue(app.app.dispatch(KeyEvent(Key.ENTER)));
                self.assertEqual(app.app.modal_depth, 0);
                self.assertFalse(app.program_active);
                self.assertIn("Respuesta: S", app.output_view.text);
            finally:
                app.interpreter.runtime.db.close();

class ProgramRuntimeTests(unittest.TestCase):
    def test_program_runtime_has_no_assistant_shell(self):
        app = SumXProgramApp();
        try:
            self.assertIs(app.app.root, app.command);
            self.assertFalse(app.command.show_prompt);
            self.assertIsNone(app.command.on_submit);
            self.assertNotIn("alt+f", app.app.bindings);
            self.assertIn("f10", app.app.bindings);
        finally:
            app.interpreter.runtime.db.close();

    def test_browse_blocks_program_and_resume_finishes(self):
        app = SumXProgramApp();
        try:
            app.run_program(
                'CREATE TABLE demo (id AUTONUM, name VARCHAR(20)); '
                'USE demo; APPEND name="Ana"; BROWSE; PRINT "done";',
                name="<test>",
            );
            self.assertTrue(app.program_active);
            self.assertEqual(app.app.modal_depth, 1);
            app.app.pop_modal();
            app._continue_program();
            self.assertFalse(app.program_active);
            self.assertTrue(any(line == "done" for line, _style in app.history_lines()));
        finally:
            app.interpreter.runtime.db.close();

    def test_argumentless_append_uses_interactive_form(self):
        app = SumXProgramApp();
        try:
            app.run_program(
                'CREATE TABLE demo (id AUTONUM, name VARCHAR(20)); USE demo; APPEND; PRINT "after";',
                name="<test>",
            );
            self.assertTrue(app.program_active);
            self.assertEqual(app.app.modal_depth, 1);
            self.assertFalse(any(line == "after" for line, _style in app.history_lines()));
        finally:
            app.interpreter.runtime.db.close();



class InterpreterTestCase(unittest.TestCase):
    def setUp(self):
        self.x = Interpreter();

    def tearDown(self):
        self.x.runtime.db.close();


class LanguageTests(InterpreterTestCase):
    def test_boolean_aliases(self):
        self.assertTrue(self.x.evaluate(".T."));
        self.assertTrue(self.x.evaluate("TRUE"));
        self.assertTrue(self.x.evaluate("ON"));
        self.assertFalse(self.x.evaluate("False"));
        self.assertFalse(self.x.evaluate("OFF"));
        self.assertTrue(self.x.evaluate("TRUE AND NOT FALSE"));
        self.assertTrue(self.x.evaluate(".T. .AND. .NOT. .F."));

    def test_null_aliases(self):
        self.assertIsNone(self.x.evaluate("NULL"));
        self.assertIsNone(self.x.evaluate(".NULL."));
        self.assertIsNone(self.x.evaluate("NONE"));
        self.assertIsNone(self.x.evaluate("NIL"));
        self.x.execute("A=NULL");
        self.assertTrue(self.x.evaluate("A IS NULL"));
        self.assertFalse(self.x.evaluate("A IS NOT NULL"));

    def test_assignment_aliases(self):
        self.x.execute("STORE 5 TO A");
        self.assertEqual(self.x.runtime.get_value("a"), 5);
        self.x.execute("LET B = A + 2");
        self.assertEqual(self.x.runtime.get_value("b"), 7);
        self.x.execute("C = B * 2");
        self.assertEqual(self.x.runtime.get_value("c"), 14);

    def test_space_and_replicate(self):
        self.assertEqual(self.x.evaluate("SPACE(30)"), " " * 30);
        self.assertEqual(self.x.evaluate('REPLICATE(" ",30)'), " " * 30);
        self.assertEqual(self.x.evaluate('REPLICATE("ab",3)'), "ababab");

    def test_say_get_read_string_fields(self):
        self.x.execute("nom=SPACE(30)");
        self.x.execute('ape=REPLICATE(" ",30)');
        first = self.x.execute('@5,1 SAY "Nombre:" GET NOM');
        second = self.x.execute('@7,1 SAY "Apellido:" GET APE');
        self.assertIsInstance(first, BatchResult);
        self.assertIsInstance(first.results[1], ScreenGetResult);
        self.assertEqual(first.results[1].field.row, 5);
        self.assertEqual(first.results[1].field.column, 9);
        self.assertEqual(first.results[1].field.width, 30);
        self.assertEqual(second.results[1].field.column, 11);
        request = self.x.execute("READ");
        self.assertIsInstance(request, ReadRequest);
        self.assertEqual(len(request.fields), 2);
        self.x.apply_read_values(request.fields, {
            "NOM": "William".ljust(30),
            "APE": "Martinez".ljust(30),
        });
        self.assertEqual(self.x.evaluate("nom"), "William".ljust(30));
        self.assertEqual(self.x.evaluate("ape"), "Martinez".ljust(30));

    def test_get_keyword_inside_say_string_does_not_confuse_parser(self):
        self.x.execute("nom=SPACE(10)");
        result = self.x.execute('@2,3 SAY "GET value:" GET nom');
        self.assertEqual(result.results[0].text, "GET value:");
        self.assertEqual(result.results[1].field.column, 14);

    def test_set_confirm_controls_runtime_field_confirmation(self):
        self.assertTrue(self.x.runtime.confirm);
        result = self.x.execute("SET CONFIRM OFF");
        self.assertFalse(self.x.runtime.confirm);
        self.assertIn("CONFIRM OFF", result.text);
        result = self.x.execute("SET CONFIRM ON");
        self.assertTrue(self.x.runtime.confirm);
        self.assertIn("CONFIRM ON", result.text);

    def test_commands_are_case_insensitive(self):
        self.x.execute("create table t (id autonum, name varchar(20))");
        self.x.execute("uSe t As demo");
        self.x.execute('aPpEnD name="x"');
        result = self.x.execute("bRoW");
        self.assertEqual(result.rows[0][1], "x");
        self.x.execute("cHaN 1");
        self.assertEqual(self.x.runtime.db.active_area, 1);

    def test_caps_sensitive_default_off(self):
        self.x.execute('Nombre="Ana"');
        self.assertEqual(self.x.evaluate("nombre"), "Ana");
        self.assertEqual(self.x.evaluate("NOMBRE"), "Ana");

    def test_caps_sensitive_on(self):
        self.x.execute("SET CAPS_SENSITIVE ON");
        self.x.execute("A=10");
        self.x.execute("a=20");
        self.assertEqual(self.x.evaluate("A"), 10);
        self.assertEqual(self.x.evaluate("a"), 20);

    def test_caps_sensitive_collision_rejected(self):
        self.x.execute("SET CAPS_SENSITIVE ON");
        self.x.execute("A=10");
        self.x.execute("a=20");
        with self.assertRaises(ValueError):
            self.x.execute("SET CAPS_SENSITIVE OFF");

    def test_quiet_default_and_debug_info(self):
        assignment = self.x.execute("A=5");
        self.assertIsInstance(assignment, OutputResult);
        self.assertFalse(assignment.emit);
        self.assertEqual(assignment.channel, "stderr");
        forced = self.x.execute("? A");
        self.assertTrue(forced.emit);
        self.assertEqual(forced.channel, "stdout");
        enabled = self.x.execute("SET DEBUG_LEVEL INFO");
        self.assertEqual(self.x.runtime.debug_level, "INFO");
        self.assertTrue(enabled.emit);
        assignment = self.x.execute("B=6");
        self.assertTrue(assignment.emit);
        self.assertEqual(assignment.level, "INFO");
        disabled = self.x.execute("SET TALK OFF");
        self.assertEqual(self.x.runtime.debug_level, "OFF");
        self.assertFalse(disabled.emit);
        self.x.execute("SET TALK ON");
        self.assertEqual(self.x.runtime.debug_level, "INFO");

    def test_debug_level_names(self):
        for name in ("OFF", "INFO", "DEBUG", "TRACE"):
            self.x.runtime.set_debug_level(name);
            self.assertEqual(self.x.runtime.debug_level, name);
        self.x.runtime.set_debug_level("ON");
        self.assertEqual(self.x.runtime.debug_level, "INFO");
        self.x.runtime.set_debug_level(".F.");
        self.assertEqual(self.x.runtime.debug_level, "OFF");

    def test_semicolon_statement_terminator(self):
        result = self.x.execute("A=1; B=2; C=A+B; ? C;");
        self.assertIsInstance(result, BatchResult);
        self.assertEqual(result.results[-1].text, "3");

    def test_hash_comments(self):
        result = self.x.execute('A=5; # initialize A\nB=7 # initialize B\n? A+B;');
        self.assertEqual(result.results[-1].text, "12");
        self.assertEqual(self.x.execute('? "# not a comment";').text, "# not a comment");
        self.assertTrue(self.x.evaluate("5 <> 4"));
        self.assertTrue(self.x.evaluate("5 != 4"));

    def test_statement_splitter_and_continuation(self):
        self.assertEqual(split_statements('A=1; B="x;y"; # c\n? B;'), ['A=1', 'B="x;y"', '? B']);
        self.assertTrue(needs_continuation('CREATE TABLE t ('));
        self.assertTrue(needs_continuation('A=SQL'));
        self.assertTrue(needs_continuation('A="""hello'));
        self.assertTrue(needs_continuation('INPUT "Continue?" answer \\'));
        self.assertFalse(needs_continuation('A=1;'));

    def test_backslash_joins_physical_lines_until_semicolon(self):
        source = (
            'INPUT "Continue?" answer \\\n'
            '    KEYS "YN" \\\n'
            '    DEFAULT "N" \\\n'
            '    TIMEOUT 10 \\\n'
            '    DIALOG ;'
        );
        statements = split_statements(source);
        self.assertEqual(len(statements), 1);
        self.assertNotIn("\\", statements[0]);
        request = self.x.execute(source);
        self.assertEqual(request.keys, "YN");
        self.assertEqual(request.default_character, "N");
        self.assertEqual(request.timeout_seconds, 10.0);
        self.assertTrue(request.dialog);

    def test_semicolon_still_ends_each_command(self):
        source = 'INPUT "Continue?" answer; KEYS "YN"; DEFAULT "N";';
        self.assertEqual(split_statements(source), ['INPUT "Continue?" answer', 'KEYS "YN"', 'DEFAULT "N"']);

    def test_triple_quoted_string(self):
        self.x.execute('memo="""line 1;\nline 2 # data""";');
        self.assertEqual(self.x.evaluate("memo"), "line 1;\nline 2 # data");

    def test_lists_dicts_and_slices(self):
        self.x.execute("A=[10,20,30,40]");
        self.assertEqual(self.x.evaluate("A[0]"), 10);
        self.assertEqual(self.x.evaluate("A[-1]"), 40);
        self.assertEqual(self.x.evaluate("A[1:3]"), [20, 30]);
        self.x.execute("A[1]=99");
        self.assertEqual(self.x.evaluate("A[1]"), 99);
        self.x.execute('D={"Name":"Ana","name":"Maria"}');
        self.assertEqual(self.x.evaluate('D["Name"]'), "Ana");
        self.assertEqual(self.x.evaluate('D["name"]'), "Maria");
        self.assertTrue(self.x.evaluate("99 IN A"));
        self.assertTrue(self.x.evaluate("100 NOT IN A"));

    def test_obj_and_attribute_assignment(self):
        self.x.execute('O=OBJ(name="Ana", active=ON, phones=["1","2"])');
        self.assertIsInstance(self.x.runtime.get_value("O"), SumObject);
        self.assertEqual(self.x.evaluate("O.name"), "Ana");
        self.assertEqual(self.x.evaluate("O.phones[1]"), "2");
        self.x.execute('O.name="Bea"');
        self.assertEqual(self.x.evaluate("O.name"), "Bea");
        self.x.execute('O.phones.append("3")');
        self.assertEqual(self.x.evaluate("LEN(O.phones)"), 3);

    def test_at_say_returns_coordinate_screen_write(self):
        result = self.x.execute('@5,5 say "La casa es roja"');
        self.assertIsInstance(result, ScreenWriteResult);
        self.assertEqual((result.row, result.column), (5, 5));
        self.assertEqual(result.text, "La casa es roja");

    def test_at_say_accepts_expressions_and_rejects_bad_coordinates(self):
        self.x.execute("A=2");
        result = self.x.execute('@ A+1, 4*2 SAY "X"');
        self.assertEqual((result.row, result.column, result.text), (3, 8, "X"));
        with self.assertRaises(Exception):
            self.x.execute('@ -1, 2 SAY "bad"');
        with self.assertRaises(Exception):
            self.x.execute('@ 1.5, 2 SAY "bad"');


class DatabaseTests(InterpreterTestCase):
    def setUp(self):
        super().setUp();
        self.x.execute("CREATE TABLE customers (id AUTONUM, name VARCHAR(80) NOT NULL, notes MEMO, balance CURRENCY, ratio FLOAT, active LOGICAL DEFAULT ON, photo BLOB)");
        self.x.execute("USE customers AS cust");

    def test_types_and_append(self):
        self.x.execute('APPEND name="Ana", notes="hola", balance=12.5, ratio=0.75, active=ON');
        result = self.x.execute("BROWSE");
        self.assertIsInstance(result, BrowseRequest);
        self.assertEqual(result.rows[0][1], "Ana");
        self.assertEqual(result.rows[0][3], "12.5000");
        self.assertEqual(result.rows[0][5], "TRUE");
        cols = self.x.runtime.db.columns("customers");
        memo = [col for col in cols if col.name == "notes"][0];
        self.assertEqual(memo.length, 65535);
        currency = [col for col in cols if col.name == "balance"][0];
        self.assertEqual(currency.logical_type, "NUMERIC");
        self.assertEqual(currency.scale, 4);

    def test_append_request(self):
        self.assertIsInstance(self.x.execute("APPEND"), AppendRequest);
        self.assertIsInstance(self.x.execute("APPEND", interactive=False), AppendRequest);

    def test_channel_semantics_and_aliases(self):
        self.assertEqual(self.x.runtime.db.active_area, 1);
        self.x.execute("CHANNEL 2");
        self.x.execute("CREATE TABLE sales (id AUTONUM, total NUMERIC(10,2))");
        self.x.execute("USE sales AS sal");
        self.assertEqual(self.x.runtime.db.current_area.table, "sales");
        self.x.execute("SEL cust");
        self.assertEqual(self.x.runtime.db.active_area, 1);
        self.assertEqual(self.x.runtime.db.current_area.table, "customers");
        self.x.execute("USE sales AS replacement");
        self.assertEqual(self.x.runtime.db.active_area, 1);
        self.assertEqual(self.x.runtime.db.current_area.table, "sales");
        self.assertEqual(self.x.runtime.db.current_area.alias, "replacement");
        self.x.execute("SELECT 2");
        self.assertEqual(self.x.runtime.db.current_area.alias, "sal");

    def test_channel_zero_and_letters(self):
        self.x.execute("CHANNEL 0");
        self.assertEqual(self.x.runtime.db.active_area, 2);
        self.x.execute("CHANNEL B");
        self.assertEqual(self.x.runtime.db.active_area, 2);
        self.x.execute("CHANNEL Z");
        self.assertEqual(self.x.runtime.db.active_area, 26);
        self.x.execute("CHANNEL 32");
        self.assertEqual(self.x.runtime.db.active_area, 32);

    def test_status_shows_alias_and_table(self):
        status = self.x.runtime.db.status();
        self.assertIn("A/1:cust=customers", status);

    def test_create_index_and_foreign_key(self):
        self.x.execute("CREATE INDEX idx_name ON customers(name)");
        rows = self.x.runtime.db.connection.execute("PRAGMA index_list(customers)").fetchall();
        self.assertTrue(any(row[1] == "idx_name" for row in rows));
        self.x.execute("CREATE TABLE orders (id AUTONUM, customer_id INTEGER REFERENCES customers(id), total NUMERIC(10,2))");
        fk = self.x.runtime.db.connection.execute("PRAGMA foreign_key_list(orders)").fetchall();
        self.assertEqual(fk[0][2], "customers");

    def test_create_form(self):
        self.x.execute("CREATE FORM customer FROM customers TITLE 'Customer entry'");
        request = self.x.execute("DO FORM customer");
        self.assertIsInstance(request, FormRequest);
        self.assertEqual(request.table, "customers");

    def test_brow_abbreviation(self):
        self.x.execute('APPEND name="Ana"');
        result = self.x.execute("BROW");
        self.assertIsInstance(result, BrowseRequest);
        self.assertEqual(result.rows[0][1], "Ana");
        self.assertEqual(result.table, "customers");


    def test_create_view_and_link_relations(self):
        self.x.execute("CREATE TABLE sales (id AUTONUM, customer_id INTEGER, total CURRENCY)");
        self.x.execute("LINK customers.id TO sales.customer_id AS customer_sales");
        relations = self.x.execute("DISPLAY RELATIONS");
        self.assertIsInstance(relations, TableResult);
        self.assertIn(["customer_sales", "customers", "id", "sales", "customer_id"], relations.rows);
        self.x.execute("CREATE VIEW customer_names AS SQL.SELECT id,name FROM customers");
        views = self.x.execute("DISPLAY VIEWS");
        self.assertTrue(any(row[0] == "customer_names" for row in views.rows));
        self.x.execute("CHANNEL 2");
        self.x.execute("USE customer_names AS cv");
        request = self.x.execute("BROWSE");
        self.assertTrue(request.readonly);

    def test_create_view_sql_block(self):
        source = """CREATE VIEW customer_names AS SQL
SELECT id,name FROM customers
ENDSQL;
""";
        result = self.x.execute(source);
        self.assertTrue(self.x.runtime.db.view_exists("customer_names"));
        self.assertIsNotNone(result);


class SqlTests(InterpreterTestCase):
    def setUp(self):
        super().setUp();
        self.x.execute("CREATE TABLE customers (id AUTONUM, name VARCHAR(40), active LOGICAL DEFAULT ON)");
        self.x.execute("USE customers AS cust");
        self.x.execute('APPEND name="Ana"');
        self.x.execute('APPEND name="Bea"');

    def test_sql_direct_scalar(self):
        result = self.x.execute("SQL.SELECT count(*) FROM customers");
        self.assertIsInstance(result, OutputResult);
        self.assertEqual(result.text, "2");

    def test_sql_scalar_assignment(self):
        self.x.execute("A=SQL.SELECT count(*) FROM customers");
        self.assertEqual(self.x.evaluate("A"), 2);
        self.x.execute("B=SQL.SCALAR SELECT count(*) FROM customers");
        self.assertEqual(self.x.evaluate("B"), 2);

    def test_sql_triple_string_assignment(self):
        source = 'A=SQL """\nSELECT count(*) FROM customers;\n""";';
        self.x.execute(source);
        self.assertEqual(self.x.evaluate("A"), 2);

    def test_sql_block_assignment(self):
        source = '''A=SQL
SELECT id, name
FROM customers
ORDER BY id
ENDSQL;
''';
        self.x.execute(source);
        value = self.x.runtime.get_value("A");
        self.assertIsInstance(value, SumCursor);
        self.assertEqual(len(value), 2);
        self.assertEqual(value[0].name, "Ana");

    def test_sql_row(self):
        self.x.execute("A=SQL.ROW SELECT id, name FROM customers WHERE id=1");
        row = self.x.runtime.get_value("A");
        self.assertIsInstance(row, SumRow);
        self.assertEqual(row.name, "Ana");
        self.assertEqual(row["NAME"], "Ana");
        self.assertEqual(row[1], "Ana");

    def test_sql_into_cursor_consumable(self):
        self.x.execute("A=SQL.SELECT id, name FROM customers ORDER BY id INTO CURSOR people");
        a = self.x.runtime.get_value("A");
        people = self.x.runtime.get_value("people");
        self.assertIs(a, people);
        self.assertIsInstance(people, SumCursor);
        result = self.x.execute("BROW people");
        self.assertEqual(result.columns, ["id", "name"]);
        self.assertEqual(result.rows[1][1], "Bea");

    def test_sql_cursor_one_row_stays_cursor(self):
        self.x.execute("A=SQL.SELECT id, name FROM customers WHERE id=1 INTO CURSOR one");
        self.assertIsInstance(self.x.runtime.get_value("one"), SumCursor);
        self.assertEqual(len(self.x.runtime.get_value("one")), 1);

    def test_sql_query_object(self):
        self.x.execute('Q=SQL.QUERY SELECT name FROM customers WHERE id=:id');
        query = self.x.runtime.get_value("Q");
        self.assertIsInstance(query, SumQuery);
        self.x.execute("R=Q.execute(id=2)");
        self.assertEqual(self.x.evaluate("R"), "Bea");

    def test_sql_exec(self):
        result = self.x.execute("SQL.EXEC UPDATE customers SET active=0 WHERE id=1");
        self.assertIsInstance(result, OutputResult);
        self.assertIn("1 rows affected", result.text);
        self.assertFalse(result.emit);
        self.assertEqual(result.channel, "stderr");

    def test_direct_sql_select_is_program_output(self):
        result = self.x.execute("SQL.SELECT count(*) FROM customers");
        self.assertIsInstance(result, OutputResult);
        self.assertTrue(result.emit);
        self.assertEqual(result.channel, "stdout");

    def test_browse_list_of_objects(self):
        self.x.execute('L=[OBJ(id=1,name="Ana"),OBJ(id=2,name="Bea")]');
        result = self.x.execute("BROW L");
        self.assertEqual(result.columns, ["id", "name"]);
        self.assertEqual(result.rows[1], ["2", "Bea"]);


class EducationalEnvironmentTests(InterpreterTestCase):
    def test_print_picture_and_transform_share_overflow_setting(self):
        result = self.x.execute('PRINT 1250.50 PICTURE "$999,999.99"');
        self.assertEqual(result.text, "$  1,250.50");
        self.assertEqual(self.x.evaluate('TRANSFORM(450.00,"**,***.99")'), "***450.00");
        self.assertEqual(self.x.evaluate('TRANSFORM("usuario12","@! NNNNNNNN")'), "USUARIO1");
        self.assertEqual(self.x.execute('? 123456 PICTURE "999"').text, "***");
        self.x.execute("SET FIELD_WRAP_OVERFLOW ON");
        self.assertEqual(self.x.evaluate('TRANSFORM("usuario12","@! NNNNNNNN")'), "USUARIO12");
        self.assertEqual(self.x.execute('? 123456 PICTURE "999"').text, "123456");

    def test_get_width_height_are_viewport_dimensions(self):
        self.x.execute('cred="ABC123450"');
        result = self.x.execute('@1,1 GET cred WIDTH 3 HEIGHT 2 PICTURE "XXX 999 990"');
        self.assertIsInstance(result, ScreenGetResult);
        field = result.field;
        self.assertEqual(field.width, 3);
        self.assertEqual(field.height, 2);
        self.assertEqual(field.picture, "XXX 999 990");
        self.assertEqual(field.value, "ABC 123 450");
        self.assertEqual(field.max_length, 11);
        self.assertFalse(field.overflow);
        self.x.execute("SET FIELD_WRAP_OVERFLOW ON");
        result = self.x.execute('@1,1 GET cred WIDTH 3 HEIGHT 2 PICTURE "XXX 999 990"');
        self.assertIsNone(result.field.max_length);
        self.assertTrue(result.field.overflow);

    def test_window_rows_and_columns_are_dynamic(self):
        size = [117, 33];
        self.x.runtime.set_screen_size_provider(lambda: tuple(size));
        self.assertEqual(self.x.evaluate("WCOLS()"), 117);
        self.assertEqual(self.x.evaluate("WROWS()"), 33);
        self.assertEqual(self.x.evaluate("SCREENCOLS()"), 117);
        self.assertEqual(self.x.evaluate("SCREENROWS()"), 33);
        size[:] = [81, 22];
        self.assertEqual(self.x.evaluate("WCOLS()"), 81);
        self.assertEqual(self.x.evaluate("WROWS()"), 22);

    def test_do_runs_prg_and_return_returns_to_caller(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder);
            child = folder / "child.prg";
            main = folder / "main.prg";
            child.write_text('X=1;\nRETURN;\nX=99;\n', encoding="utf-8");
            main.write_text('DO child;\nY=2;\n', encoding="utf-8");
            self.x.run_file(main);
            self.assertEqual(self.x.evaluate("X"), 1);
            self.assertEqual(self.x.evaluate("Y"), 2);

    def test_compiler_output_is_readable_runtime_dependent_python(self):
        generated = compile_source('PRINT "Hello";\n', source_name="hello.prg");
        self.assertIn("from sumx.compiler_support import GeneratedProgram;", generated);
        self.assertIn('# sumX line 1: PRINT "Hello"', generated);
        self.assertIn("program.statement", generated);
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "hello.prg";
            output = Path(folder) / "hello.py";
            source.write_text('PRINT "Hello";\n', encoding="utf-8");
            _generated, built = compile_file(source, output=output);
            self.assertEqual(built, output);
            self.assertTrue(output.stat().st_mode & 0o111);

    def test_compiled_program_keeps_source_directory_for_do(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder);
            child = folder / "child.prg";
            source = folder / "main.prg";
            output = folder / "main.py";
            child.write_text('Z=7;\n', encoding="utf-8");
            source.write_text('DO child;\nPRINT Z;\n', encoding="utf-8");
            generated = compile_source(source.read_text(encoding="utf-8"), source_name=str(source));
            self.assertIn("DO child", generated);
            # The generated runtime helper keeps main.prg as the caller context,
            # so relative DO paths resolve beside the original source file.
            from sumx.compiler_support import GeneratedProgram;
            program = GeneratedProgram(source_name=str(source));
            try:
                self.assertTrue(program.statement("DO child", source_line=1));
                self.assertEqual(program.interpreter.evaluate("Z"), 7);
            finally:
                program.finish();

    def test_every_help_topic_has_a_functional_example(self):
        self.assertGreater(len(TOPICS), 0);
        for topic in TOPICS.values():
            self.assertTrue(topic.example.strip(), topic.name);
            self.assertIn("## Functional example", topic.markdown());
        self.assertEqual(find_topic("SCREENCOLS").name, "WCOLS");
        self.assertEqual(find_topic("SCREENROWS").name, "WROWS");


class ConsoleTests(unittest.TestCase):
    def test_shell_escape_appends_output_to_command_history(self):
        app = SumXConsoleApp();
        try:
            completed = SimpleNamespace(stdout="bin\netc\n", returncode=0);
            with patch("sumx.console.subprocess.run", return_value=completed) as run:
                app.command.set_value("!ls /");
                self.assertTrue(app.command.submit());
            run.assert_called_once();
            self.assertEqual(run.call_args.args[0], "ls /");
            rendered = [line for line, _style in app.command.output];
            self.assertIn(". !ls /", rendered);
            self.assertIn("bin", rendered);
            self.assertIn("etc", rendered);
        finally:
            app.interpreter.runtime.db.close();

    def test_shell_escape_reports_nonzero_exit(self):
        app = SumXConsoleApp();
        try:
            completed = SimpleNamespace(stdout="not found\n", returncode=127);
            with patch("sumx.console.subprocess.run", return_value=completed):
                app._submit("!missing-command", app.command);
            self.assertIn(("not found", "command"), app.command.output);
            self.assertIn(("[shell exit 127]", "command_error"), app.command.output);
        finally:
            app.interpreter.runtime.db.close();

    def test_command_panel_uses_solid_command_background(self):
        app = SumXConsoleApp();
        try:
            panel = app.app.root.items[0].widget;
            self.assertEqual(panel.content_style, "command");
        finally:
            app.interpreter.runtime.db.close();

    def test_at_say_is_written_to_command_screen_layer(self):
        app = SumXConsoleApp();
        try:
            result = app.interpreter.execute('@5,5 SAY "hello"');
            app._handle_result(result);
            self.assertEqual(app.command.screen[(5, 5)], ("h", "command"));
            self.assertEqual(app.command.screen[(5, 9)], ("o", "command"));
        finally:
            app.interpreter.runtime.db.close();


    def test_multiline_read_tab_accepts_and_archives_fields_to_history(self):
        app = SumXConsoleApp();
        try:
            source = '''
cred = "ABC123450";
notes = "A multiline GET can be narrower and shorter than its logical value.";
@ 1,1 PRINT "Credential: " GET cred WIDTH 3 PICTURE "XXX 999 990";
@ 3,1 PRINT "Notes:";
@ 4,1 GET notes WIDTH 30 HEIGHT 4;
READ;
PRINT cred;
PRINT notes;
''';
            app.run_program(source, name="get_viewport.prg");
            self.assertTrue(app.program_active);
            self.assertTrue(app.command.read_active);
            self.assertEqual(app.command.read_index, 0);
            self.assertTrue(app.command.handle_event(KeyEvent(Key.TAB)));
            self.assertEqual(app.command.read_index, 1);
            self.assertTrue(app.command.handle_event(KeyEvent(Key.TAB)));
            self.assertFalse(app.command.read_active);
            self.assertFalse(app.program_active);
            self.assertFalse(app.command.fields);
            self.assertFalse(app.command.screen);
            history = [line for line, _style in app.command.output];
            self.assertTrue(any("Credential:" in line and "ABC" in line for line in history));
            self.assertTrue(any("Notes:" in line for line in history));
            self.assertIn("ABC 123 450", history);
            self.assertIn("A multiline GET can be narrower and shorter than its logical value.", history);
        finally:
            app.interpreter.runtime.db.close();

    def test_append_uses_type_aware_record_form_fields(self):
        app = SumXConsoleApp();
        try:
            app.interpreter.execute("CREATE TABLE t (id AUTONUM, name CHARACTER(6), amount NUMERIC(6,2), active LOGICAL)");
            app.interpreter.execute("USE t");
            columns = app.interpreter.runtime.db.columns("t");
            fields = [app._field_for_column(column) for column in columns];
            by_name = {field.name: field for field in fields};
            self.assertTrue(by_name["id"].readonly);
            self.assertEqual(by_name["name"].mask, "XXXXXX");
            self.assertEqual(by_name["amount"].mask, "9990.00");
            self.assertEqual(by_name["active"].kind, "logical");
        finally:
            app.interpreter.runtime.db.close();

    def test_interactive_append_form_is_editable_and_ctrl_end_saves(self):
        app = SumXConsoleApp();
        try:
            app.interpreter.execute("CREATE TABLE t (id AUTONUM, name VARCHAR(20), active LOGICAL)");
            app.interpreter.execute("USE t");
            request = app.interpreter.execute("APPEND", interactive=True);
            app._handle_result(request);
            self.assertEqual(app.app.modal_depth, 1);
            dialog = app.app.root;
            form = dialog.child.children()[0] if False else dialog.child.items[0].widget;
            name = form.control("name");
            app.app.focus.set(name);
            name.set("");
            name.cursor = 0;
            self.assertTrue(app.app.dispatch(KeyEvent("a", text="Ana")));
            self.assertEqual(name.value, "Ana");
            self.assertTrue(app.app.dispatch(KeyEvent(Key.END, ctrl=True)));
            self.assertEqual(app.interpreter.runtime.db.reccount(), 1);
            _columns, rows = app.interpreter.runtime.db.browse("t");
            self.assertEqual(rows[0][1], "Ana");
        finally:
            app.interpreter.runtime.db.close();

    def test_browse_request_updates_workarea_record_on_selection(self):
        app = SumXConsoleApp();
        try:
            app.interpreter.execute("CREATE TABLE t (id AUTONUM, name VARCHAR(20))");
            app.interpreter.execute("USE t");
            app.interpreter.execute('APPEND name="Ana"');
            app.interpreter.execute('APPEND name="Luis"');
            request = app.interpreter.execute("BROWSE");
            self.assertIsInstance(request, BrowseRequest);
            app._show_browse(request);
            browser = app.app.root.child.items[0].widget;
            browser.select(1);
            self.assertEqual(app.interpreter.runtime.db.recno(), 2);
            app.app.pop_modal();
        finally:
            app.interpreter.runtime.db.close();

    def test_program_runner_pauses_on_browse_and_table_dialogs(self):
        app = SumXConsoleApp();
        try:
            source = '''
CREATE TABLE t (id AUTONUM, name VARCHAR(20));
USE t;
APPEND name="Ana";
BROWSE;
X=5;
DISPLAY STRUCTURE;
Y=7;
''';
            app.run_program(source, name="demo.prg");
            self.assertTrue(app.program_active);
            self.assertEqual(app.app.modal_depth, 1);
            self.assertEqual(app.app.root.title, "Browse: t");
            self.assertFalse(app.interpreter.runtime.has_value("X"));

            app.app.root.cancel();
            self.assertTrue(app.program_active);
            self.assertEqual(app.app.modal_depth, 1);
            self.assertEqual(app.app.root.title, "Structure: t");
            self.assertEqual(app.interpreter.evaluate("X"), 5);
            self.assertFalse(app.interpreter.runtime.has_value("Y"));

            app.app.root.cancel();
            self.assertFalse(app.program_active);
            self.assertEqual(app.app.modal_depth, 0);
            self.assertEqual(app.interpreter.evaluate("Y"), 7);
        finally:
            app.interpreter.runtime.db.close();


    def test_help_opens_explorer_dialog(self):
        app = SumXConsoleApp();
        try:
            result = app.interpreter.execute("HELP", interactive=True);
            self.assertIsInstance(result, HelpRequest);
            app._handle_result(result);
            self.assertEqual(app.app.modal_depth, 1);
            self.assertEqual(app.app.root.title, "sumX Help");
            body = app.app.root.child.items[0].widget;
            viewer = body.items[1].widget;
            self.assertIn("Every documented language feature", viewer.markdown);
            app.app.root.cancel();
        finally:
            app.interpreter.runtime.db.close();

    def test_browse_enter_edits_current_record(self):
        app = SumXConsoleApp();
        try:
            app.interpreter.execute("CREATE TABLE t (id AUTONUM, name VARCHAR(20), active LOGICAL)");
            app.interpreter.execute("USE t");
            app.interpreter.execute('APPEND name="Ana", active=ON');
            app.interpreter.execute('APPEND name="Luis", active=OFF');
            request = app.interpreter.execute("BROWSE");
            app._show_browse(request);
            browser = app.app.root.child.items[0].widget;
            browser.select(1);
            app.app.focus.set(browser.table);
            self.assertTrue(app.app.dispatch(KeyEvent(Key.ENTER)));
            self.assertEqual(app.app.modal_depth, 2);
            form = app.app.root.child.items[0].widget;
            name = form.control("name");
            app.app.focus.set(name);
            name.set("Beatriz");
            self.assertTrue(app.app.dispatch(KeyEvent(Key.END, ctrl=True)));
            self.assertEqual(app.app.modal_depth, 1);
            self.assertEqual(app.interpreter.runtime.db.record_at(2, table="t")["name"], "Beatriz");
            app.app.root.cancel();
        finally:
            app.interpreter.runtime.db.close();

    def test_append_has_record_navigation_button_bar(self):
        app = SumXConsoleApp();
        try:
            app.interpreter.execute("CREATE TABLE t (id AUTONUM, name VARCHAR(20))");
            app.interpreter.execute("USE t");
            app._handle_result(app.interpreter.execute("APPEND"));
            content = app.app.root.child;
            buttons = content.items[2].widget;
            labels = [item.widget.label for item in buttons.items];
            self.assertEqual(labels, ["First", "Prev", "Next", "Last", "Search", "Ok", "Cancel", "Exit"]);
            app.app.root.cancel();
        finally:
            app.interpreter.runtime.db.close();


class ConfigurationThemeTests(unittest.TestCase):
    def test_console_saves_and_reloads_theme(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "sumx.json";
            app = SumXConsoleApp(config_path=config);
            try:
                self.assertEqual(app.app.theme.name, "XBASE");
                self.assertTrue(app.set_theme("Ralesk's MC"));
                self.assertTrue(app.save_configuration());
                self.assertTrue(config.exists());
            finally:
                app.interpreter.runtime.db.close();
            reloaded = SumXConsoleApp(config_path=config);
            try:
                self.assertEqual(reloaded.app.theme.name, "Ralesk's MC");
            finally:
                reloaded.interpreter.runtime.db.close();

    def test_editor_saves_display_options_with_theme(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "demo.prg";
            config = Path(directory) / "sumx.json";
            source.write_text('PRINT "hello"\n', encoding="utf-8");
            app = SumXEditorApp(source, config_path=config);
            try:
                app.set_theme("DOS");
                app.editor.show_spaces = True;
                app.editor.show_tabs = True;
                app.editor.show_line_endings = True;
                app.editor.show_control_chars = True;
                self.assertTrue(app.save_configuration());
            finally:
                app.interpreter.runtime.db.close();
            reloaded = SumXEditorApp(source, config_path=config);
            try:
                self.assertEqual(reloaded.app.theme.name, "DOS");
                self.assertTrue(reloaded.editor.show_spaces);
                self.assertTrue(reloaded.editor.show_tabs);
                self.assertTrue(reloaded.editor.show_line_endings);
                self.assertTrue(reloaded.editor.show_control_chars);
            finally:
                reloaded.interpreter.runtime.db.close();

    def test_program_runtime_uses_saved_theme_without_assistant(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "sumx.json";
            config.write_text("{\"theme\": \"Ralesk's MC\"}\n", encoding="utf-8");
            app = SumXProgramApp(config_path=config);
            try:
                self.assertEqual(app.app.theme.name, "Ralesk's MC");
                self.assertIs(app.app.root, app.command);
                self.assertFalse(app.command.show_prompt);
            finally:
                app.interpreter.runtime.db.close();


class FileTests(unittest.TestCase):
    def test_run_file_continuation(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "demo.prg";
            path.write_text('# sumX semicolon/comments demo\nCREATE TABLE t (\n id AUTONUM,\n name VARCHAR(20)\n);\nUSE t; APPEND name="x";\n? RECCOUNT(); # should print one\n', encoding="utf-8");
            x = Interpreter();
            try:
                results = x.run_file(path);
                self.assertEqual(results[-1].text, "1");
            finally:
                x.runtime.db.close();

    def test_run_file_sql_block(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sql.prg";
            path.write_text('CREATE TABLE t (id AUTONUM, name VARCHAR(20));\nUSE t;\nAPPEND name="x";\nA=SQL\nSELECT count(*) FROM t;\nENDSQL;\n? A;\n', encoding="utf-8");
            x = Interpreter();
            try:
                results = x.run_file(path);
                self.assertEqual(results[-1].text, "1");
            finally:
                x.runtime.db.close();



    def test_editor_program_map_preselects_current_procedure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "map_current.prg";
            path.write_text("PROCEDURE One\nRETURN\n\nPROCEDURE Two\n? 2\nRETURN\n", encoding="utf-8");
            app = SumXEditorApp(path);
            app.editor.goto_line(5, 1);
            self.assertTrue(app.symbol_map_dialog());
            listing = app.app.focus.current;
            self.assertEqual(listing.current_value.name.strip(), "Two");
            app.app.pop_modal();

if __name__ == "__main__":
    unittest.main();

class InputStatementTests(unittest.TestCase):
    def setUp(self):
        self.x = Interpreter();

    def tearDown(self):
        self.x.runtime.db.close();

    def test_basic_like_input_creates_string_variable(self):
        from sumx.results import InputRequest;
        request = self.x.execute('INPUT "What is your name? " name');
        self.assertIsInstance(request, InputRequest);
        self.assertEqual(request.prompt, "What is your name? ");
        self.assertEqual(request.target, "name");
        self.x.apply_input_value(request, "Ada");
        self.assertEqual(self.x.runtime.get_value("name"), "Ada");

    def test_input_preserves_existing_numeric_type(self):
        self.x.runtime.set_value("age", 0);
        request = self.x.execute('INPUT "Age? " age');
        self.x.apply_input_value(request, "42");
        self.assertEqual(self.x.runtime.get_value("age"), 42);
        self.assertIsInstance(self.x.runtime.get_value("age"), int);

    def test_accept_is_xbase_character_input(self):
        from sumx.results import InputRequest;
        self.x.runtime.set_value("cNombre", 123);
        request = self.x.execute('ACCEPT "Por favor, ingresa tu nombre: " TO cNombre;');
        self.assertIsInstance(request, InputRequest);
        self.assertEqual(request.command, "ACCEPT");
        self.assertTrue(request.text_only);
        self.assertEqual(request.prompt, "Por favor, ingresa tu nombre: ");
        self.x.apply_input_value(request, "Ada");
        self.assertEqual(self.x.runtime.get_value("cNombre"), "Ada");

    def test_input_blocks_remaining_statements(self):
        from sumx.results import InputRequest;
        request = self.x.execute('INPUT "Name? " name; PRINT name');
        self.assertIsInstance(request, InputRequest);
        self.assertEqual(request.remaining, ["PRINT name"]);

class ExtendedInputStatementTests(unittest.TestCase):
    def setUp(self):
        self.x = Interpreter();

    def tearDown(self):
        self.x.runtime.db.close();

    def test_input_options_are_parsed(self):
        from sumx.results import InputRequest;
        request = self.x.execute('INPUT "Password: " password HIDDEN MASK "***" WIDTH 12 DIALOG');
        self.assertIsInstance(request, InputRequest);
        self.assertTrue(request.hidden);
        self.assertEqual(request.mask, "***");
        self.assertEqual(request.width, 12);
        self.assertTrue(request.dialog);

    def test_input_choice_timeout_options(self):
        request = self.x.execute('INPUT "Continue? " answer KEYS "YN" DEFAULT "N" TIMEOUT 10 CASE_SENSITIVE');
        self.assertEqual(request.keys, "YN");
        self.assertEqual(request.default_character, "N");
        self.assertEqual(request.timeout_seconds, 10.0);
        self.assertTrue(request.case_sensitive);
        self.x.apply_input_value(request, "Y");
        self.assertEqual(self.x.runtime.get_value("answer"), "Y");

    def test_input_picture_formats_character_result(self):
        request = self.x.execute('INPUT "Phone: " phone PICTURE "(999) 999-9999" WIDTH 14');
        self.x.apply_input_value(request, "1234567890");
        self.assertEqual(self.x.runtime.get_value("phone"), "(123) 456-7890");

    def test_multiline_input_rejects_masking_features_for_now(self):
        with self.assertRaises(Exception):
            self.x.execute('INPUT "Secret: " secret HEIGHT 3 HIDDEN');


class CompatibilitySyntaxTests(InterpreterTestCase):
    def test_symbolic_logical_aliases(self):
        self.assertFalse(self.x.evaluate("TRUE && FALSE"));
        self.assertTrue(self.x.evaluate("FALSE || TRUE"));
        self.assertTrue(self.x.evaluate("TRUE ^^ FALSE"));
        self.assertTrue(self.x.evaluate("~FALSE"));
        self.assertTrue(self.x.evaluate("¬FALSE"));

    def test_ampersand_comment_is_opt_in(self):
        self.assertFalse(self.x.evaluate("TRUE && FALSE"));
        result = self.x.execute('SET AMPERSAND_COMMENT ON\nA=5 && classic comment\n? A');
        self.assertTrue(self.x.runtime.ampersand_comment);
        self.assertEqual(result.results[-1].text, "5");
        self.assertEqual(split_statements('A=1 && B=2'), ['A=1 && B=2']);
        self.assertEqual(split_statements('A=1 && comment', ampersand_comment=True), ['A=1']);

    def test_legacy_semicolon_line_continuation(self):
        source = (
            'SET LINE_CONTINUATION TO SEMICOLON\n'
            'INPUT "Continue?" answer ;\n'
            '    KEYS "YN" ;\n'
            '    DEFAULT "N" ;\n'
            '    DIALOG\n'
        );
        result = self.x.execute(source);
        request = result.results[-1];
        self.assertEqual(self.x.runtime.line_continuation, "SEMICOLON");
        self.assertEqual(request.keys, "YN");
        self.assertEqual(request.default_character, "N");
        self.assertTrue(request.dialog);
        self.assertEqual(split_statements('A=1; B=2', line_continuation='SEMICOLON'), ['A=1', 'B=2']);

    def test_optional_then_forms(self):
        self.assertEqual(self.x.execute('IF 5==5 THEN PRINT "listo"').text, "listo");
        block = self.x.execute('A=5\nIF A==5\nPRINT "LISTO"\nENDIF');
        self.assertEqual(block.results[-1].text, "LISTO");
        block_then = self.x.execute('A=5\nIF A==5 THEN\nPRINT "LISTO"\nPRINT "ALGO MÁS"\nENDIF');
        self.assertEqual([item.text for item in block_then.results if isinstance(item, OutputResult) and item.emit], ["LISTO", "ALGO MÁS"]);

    def test_if_else_and_nested_blocks(self):
        result = self.x.execute('A=4\nIF A==5 THEN\nPRINT "NO"\nELSE\nIF A==4 THEN PRINT "SI"\nENDIF');
        self.assertEqual(result.results[-1].text, "SI");

    def test_define_window_maps_to_window_request(self):
        from sumx.results import WindowRequest;
        defined = self.x.execute('DEFINE WINDOW wDialogo FROM 8,15 TO 16,65 TITLE " Confirmación " SHADOW PANEL COLOR SCHEME 5');
        self.assertIn("wDialogo", defined.text);
        request = self.x.execute('ACTIVATE WINDOW wDialogo');
        self.assertIsInstance(request, WindowRequest);
        self.assertEqual(request.definition["width"], 51);
        self.assertEqual(request.definition["height"], 9);
        self.assertTrue(request.definition["shadow"]);
        self.assertTrue(request.definition["panel"]);
        self.assertEqual(request.definition["color_scheme"], 5);
        write = self.x.execute('@1,1 PRINT "Hola"');
        self.assertEqual(write.window, "wDialogo");
        self.x.execute('DEACTIVATE WINDOW wDialogo');
        self.x.execute('RELEASE WINDOW wDialogo');

    def test_compiler_emits_readable_python_if(self):
        generated = compile_source('A=5\nIF A==5 THEN\nPRINT "LISTO"\nELSE\nPRINT "NO"\nENDIF\n');
        self.assertIn("if program.condition('A==5'", generated);
        self.assertIn('program.statement(\'PRINT "LISTO"\'', generated);

class CompiledThemeTests(unittest.TestCase):
    def test_custom_theme_is_embedded_as_python_data(self):
        from sumtui import THEMES, make_theme;
        custom = make_theme("Ralesk's MC").copy(name="Teaching MC", style_overrides=(("syntax_keyword", "bold #abcdef"),));
        THEMES[custom.name] = custom;
        try:
            generated = compile_source('PRINT "Hello";\n', source_name="hello.prg", theme=custom.name);
            self.assertIn("# Compile-time theme: Teaching MC", generated);
            self.assertIn("PROGRAM_THEME_NAME = None", generated);
            self.assertIn("Teaching MC", generated);
            self.assertIn("#abcdef", generated);
        finally:
            THEMES.pop(custom.name, None);

    def test_builtin_theme_compiles_by_name_without_user_config_dependency(self):
        generated = compile_source('PRINT "Hello";\n', source_name="hello.prg", theme="DOS");
        self.assertIn("PROGRAM_THEME_NAME = 'DOS'", generated);
        self.assertIn("PROGRAM_THEME_DATA = None", generated);

    def test_browse_button_bar_contains_new_record_action(self):
        app = SumXConsoleApp();
        try:
            app.interpreter.execute("CREATE TABLE t (id AUTONUM, name VARCHAR(20))");
            app.interpreter.execute("USE t");
            request = app.interpreter.execute("BROWSE");
            app._show_browse(request);
            content = app.app.root.child;
            buttons = content.items[1].widget;
            labels = [item.widget.label for item in buttons.items];
            self.assertEqual(labels, ["First", "Prev", "Next", "Last", "Search", "New*", "Edit", "Exit"]);
            app.app.root.cancel();
        finally:
            app.interpreter.runtime.db.close();

class BrowseNewRecordTests(unittest.TestCase):
    def test_browse_new_appends_refreshes_and_selects_new_record(self):
        app = SumXConsoleApp();
        try:
            app.interpreter.execute("CREATE TABLE t (id AUTONUM, name VARCHAR(20))");
            app.interpreter.execute("USE t");
            request = app.interpreter.execute("BROWSE");
            app._show_browse(request);
            browse_dialog = app.app.root;
            content = browse_dialog.child;
            browser = content.items[0].widget;
            buttons = content.items[1].widget;
            new_button = next(item.widget for item in buttons.items if item.widget.label == "New*");
            self.assertTrue(new_button.press());
            self.assertEqual(app.app.modal_depth, 2);
            form = app.app.root.child.items[0].widget;
            name = form.control("name");
            app.app.focus.set(name);
            name.set("Ana");
            self.assertTrue(app.app.dispatch(KeyEvent(Key.END, ctrl=True)));
            self.assertEqual(app.app.modal_depth, 1);
            self.assertEqual(app.interpreter.runtime.db.reccount_for("t"), 1);
            self.assertEqual(app.interpreter.runtime.db.record_at(1, table="t")["name"], "Ana");
            self.assertEqual(browser.selected, 0);
            app.app.root.cancel();
        finally:
            app.interpreter.runtime.db.close();


class WorkspaceIDEtests(unittest.TestCase):
    def test_editor_workspace_has_code_output_command_windows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "windows.prg";
            path.write_text('PRINT "hello"\n', encoding="utf-8");
            app = SumXEditorApp(path);
            try:
                self.assertEqual([window.name for window in app.workspace.windows], ["output", "command", "code"]);
                self.assertIs(app.workspace.active_window, app.code_window);
                self.assertTrue(app.close_current_window(app.command_window));
                self.assertFalse(app.command_window.visible);
                self.assertTrue(app.activate_window(app.command_window));
                self.assertTrue(app.command_window.visible);
                self.assertTrue(app.toggle_window_maximize(app.output_window));
                self.assertTrue(app.output_window.maximized);
                self.assertTrue(app.toggle_window_maximize(app.output_window));
                self.assertFalse(app.output_window.maximized);
            finally:
                pass;

    def test_program_output_goes_to_output_window_not_command_history(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.prg";
            path.write_text('PRINT "hello"\n', encoding="utf-8");
            app = SumXEditorApp(path);
            try:
                app.run_buffer();
                for _ in range(20):
                    if not app._program_active:
                        break;
                    app._program_idle();
                self.assertIn("hello", app.output_view.text);
            finally:
                pass;

class EditorShortcutMapTests(unittest.TestCase):
    def test_f2_program_map_ctrl_q_and_scrolled_output(self):
        from sumtui import TextViewPane, CommandWindowPane;
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'map.prg';
            path.write_text('PROCEDURE Hello\nRETURN\nFUNCTION Add\nRETURN 1\n', encoding='utf-8');
            app = SumXEditorApp(path);
            names = {item.name for item in app.symbol_map()};
            self.assertIn('Hello', names);
            self.assertIn('Add', names);
            self.assertIsInstance(app.output_window.child, TextViewPane);
            self.assertIsInstance(app.command_window.child, CommandWindowPane);
            self.assertIn('ctrl+q', app.app.bindings);
            self.assertIn('ctrl+x', app.app.bindings);
            self.assertIn('ctrl+r', app.app.bindings);
            self.assertIn('ctrl+tab', app.app.bindings);
            self.assertIn('alt+enter', app.app.bindings);

class SumDiffMenuIntegrationTests(unittest.TestCase):
    def test_editor_file_menu_contains_compare_with(self):
        from sumx.editor_app import SumXEditorApp;
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "demo.prg";
            path.write_text('? "hello"\n', encoding="utf-8");
            app = SumXEditorApp(path);
            labels = [item.label for item in app._editor_menus()[0].items if getattr(item, "label", "")];
            self.assertIn("Compare with...", labels);


class SumXDefaultWorkspaceTests(unittest.TestCase):
    def test_sumx_without_arguments_opens_common_ide_with_command_focused(self):
        import sumx.cli as cli;
        fake_window = object();
        with patch("sumx.cli.SumXEditorApp") as editor_class, patch("sys.stdin.isatty", return_value=True), patch("sys.stdout.isatty", return_value=True):
            editor = editor_class.return_value;
            editor.command_window = fake_window;
            editor.run.return_value = 23;
            self.assertEqual(cli.main([]), 23);
            editor_class.assert_called_once();
            editor.activate_workspace_window.assert_called_once_with(fake_window);
            editor._update_status.assert_called_once();

    def test_sumx_console_switch_keeps_classic_command_frontend(self):
        import sumx.cli as cli;
        with patch("sumx.cli.SumXConsoleApp") as console_class, patch("sys.stdin.isatty", return_value=True), patch("sys.stdout.isatty", return_value=True):
            console_class.return_value.run.return_value = 17;
            self.assertEqual(cli.main(["--console"]), 17);
            console_class.assert_called_once();

    def test_help_can_copy_current_functional_example(self):
        from sumtui.clipboard import clipboard;
        topic = find_topic("IF");
        app = SumXConsoleApp();
        try:
            app._show_help(topic.markdown(), title="sumX Help - IF");
            self.assertTrue(app.app.dispatch(KeyEvent(Key.F6)));
            self.assertEqual(clipboard.paste_text(), topic.example);
            app.app.root.cancel();
        finally:
            app.interpreter.runtime.db.close();


class EditableHelpMarkdownTests(unittest.TestCase):
    def test_sumx_help_uses_packaged_compiled_database_with_editable_source(self):
        from importlib.resources import files;
        from sumx.helpdb import CORPUS, find_topic;
        source = files("sumx").joinpath("help.md").read_text(encoding="utf-8");
        compiled = files("sumx").joinpath("help.helpdb").read_text(encoding="utf-8");
        self.assertIn("# sumX Help", source);
        self.assertIn('"schema_version": 1', compiled);
        self.assertGreater(len(CORPUS.topics), 10);
        self.assertEqual(find_topic("!").name, "SHELL ESCAPE");

    def test_classic_help_f2_opens_topic_map(self):
        app = SumXConsoleApp();
        try:
            topic = find_topic("IF");
            app._show_help(topic.markdown(), title="sumX Help - IF");
            self.assertTrue(app.app.dispatch(KeyEvent(Key.F2)));
            self.assertIsInstance(app.app.focus.current, ListView);
            app.app.pop_modal();
            app.app.pop_modal();
        finally:
            app.interpreter.runtime.db.close();
