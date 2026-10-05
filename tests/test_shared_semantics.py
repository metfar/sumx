#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sumx.expressions import ExpressionEvaluator;

class DB:
    def recno(self): return 1;
    def reccount(self): return 0;
    @property
    def current_area(self): return type("A",(),{"alias":"","table":""})();
    active_area=1;
class RT:
    db=DB(); field_wrap_overflow=False; ampersand_comment=False;
    def screen_size(self): return (80,25);
    def cursor(self,query=True): return 1;
    def messagebox(self,*args): return 1;

def ev(source): return ExpressionEvaluator(RT()).evaluate(source);

def test_shared_text_and_formats():
    assert ev('REPEAT("ab",3)')=="ababab";
    assert ev('MID("abcdef",0,1)')=="a";
    assert ev('INSTR("abcdef","cd")')==2;
    assert ev('INSTR("abcdef","xx")')==-1;
    assert ev('TRIM("...hola...",".")')=="hola";
    assert ev('ILIKE("Montevideo","monte%")') is True;
    assert ev('NUMFORMAT(5,"$ 0000.00")')=="$ 0005.00";
