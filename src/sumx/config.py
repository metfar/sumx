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
import json;
import os;
from pathlib import Path;

from sumtui import THEMES;


DEFAULT_THEME = "XBASE";


def default_config_path():
    base = os.environ.get("XDG_CONFIG_HOME");
    if base:
        return Path(base).expanduser() / "sumx" / "config.json";
    return Path("~/.config/sumx/config.json").expanduser();


def load_config(path=None):
    target = Path(path).expanduser() if path is not None else default_config_path();
    try:
        data = json.loads(target.read_text(encoding="utf-8"));
        return data if isinstance(data, dict) else {};
    except (OSError, ValueError, TypeError):
        return {};


def save_config(data, path=None):
    target = Path(path).expanduser() if path is not None else default_config_path();
    target.parent.mkdir(parents=True, exist_ok=True);
    temporary = target.with_name(target.name + ".tmp");
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8");
    temporary.replace(target);
    return target;


def theme_names():
    preferred = ("XBASE", "Ralesk's MC", "DBASE", "FOXPRO", "DOS", "RAR", "Dark", "Light", "C64", "MSX", "ZX");
    names = [name for name in preferred if name in THEMES];
    names.extend(name for name in THEMES if name not in names);
    return tuple(names);


def resolve_theme(requested=None, config=None):
    candidate = requested or (config or {}).get("theme") or DEFAULT_THEME;
    for name in THEMES:
        if str(name).casefold() == str(candidate).casefold():
            return name;
    return DEFAULT_THEME;
