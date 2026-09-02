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

from sumui import DialogSpec, FieldSpec;


def messagebox_spec(text, flags=0, title="Message"):
    numeric = int(flags or 0);
    low = numeric & 0x0F;
    icon = numeric & 0xF0;
    kind = {0x10: "error", 0x20: "question", 0x30: "warning", 0x40: "info"}.get(icon, "info");
    buttons = ("ok",);
    if low == 4:
        buttons = ("yes", "no");
    elif low == 1:
        buttons = ("ok", "cancel");
    return DialogSpec(
        kind=kind, title=str(title or "Message"), text=str(text),
        options=(("flags", numeric), ("buttons", list(buttons))),
    ).normalize();


def get_field_spec(name, default="", width=None, max_length=None, picture="", confirm=True, valid_values=(), validation_error="Invalid value"):
    return FieldSpec(
        name=str(name), label=str(name), default=default, width=width, max_length=max_length,
        picture=str(picture or ""), confirm=bool(confirm), valid_values=tuple(valid_values or ()),
        validation_error=str(validation_error or "Invalid value"),
    ).normalize();
