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
from sumtui import THEMES, make_theme;
from sumx.compiler import compile_source;


custom = make_theme("ZX").copy(name="Classroom ZX", style_overrides=(("syntax_keyword", "bold #abcdef"),));
THEMES[custom.name] = custom;
python_source = compile_source('PRINT "Hello";\n', source_name="lesson.prg", theme=custom.name);
for line in python_source.splitlines():
    if line.startswith("# Compile-time theme:") or line.startswith("PROGRAM_THEME_"):
        print(line);
