#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#pylint:disable=W0301
import sumx.expressions as expressions;
from sumx.expressions import ExpressionEvaluator;
class DB:
    active_area=1;
    def recno(self): return 1;
    def reccount(self): return 1;
    @property
    def current_area(self): return type("Area",(),{"alias":"","table":""})();
class Runtime:
    ampersand_comment=False; db=DB(); field_wrap_overflow=False;
    def get_value(self,name): raise KeyError(name);
    def screen_size(self): return (80,25);
    def messagebox(self,*args): return 0;

def test_readrds_calls_common_sumdata(monkeypatch):
    monkeypatch.setattr(expressions,"read_rds",lambda path:{"path":path});
    ev=ExpressionEvaluator(Runtime()); assert ev.evaluate('READRDS("x.rds")')=={"path":"x.rds"};
