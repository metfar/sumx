from sumui import CursorState, TextScreen;
from sumx.interpreter import Interpreter;


def test_sumx_common_aliases_grid_and_cursor():
    interp=Interpreter(); size=[80,25]; states=[];
    interp.runtime.set_screen_size_provider(lambda: tuple(size));
    interp.runtime.set_text_screen(TextScreen(size_provider=interp.runtime.screen_size,cursor_setter=states.append));
    assert interp.evaluate("TRUE") is True and interp.evaluate("true") is True;
    assert interp.evaluate("FALSE") is False and interp.evaluate("false") is False;
    for name in ("NULL","Null","null","NIL","Nil","nil","None","none"):
        assert interp.evaluate(name) is None;
    assert interp.evaluate("COLS()") == 80 and interp.evaluate("ROWS()") == 25;
    size[:]=[43,18]; assert interp.evaluate("COLS()") == 43 and interp.evaluate("ROWS()") == 18;
    assert interp.execute("CURSOR OFF",interactive=False) is None;
    assert interp.evaluate("CURSOR()") == 0;
    interp.execute("CURSOR ON",interactive=False); assert interp.evaluate("CURSOR()") == 1;
    interp.execute("CURSOR BLOCK",interactive=False); assert interp.evaluate("CURSOR()") == 2;
    assert states == [CursorState.HIDDEN,CursorState.NORMAL,CursorState.BLOCK];
