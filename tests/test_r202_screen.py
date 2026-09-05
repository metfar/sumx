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


def test_sumx_pause_delay_stops_statement_batch_until_resumed():
    from sumx.results import BatchResult, DelayRequest;
    interp = Interpreter(); states = [];
    interp.runtime.set_text_screen(TextScreen(size_provider=lambda: (80,25), cursor_setter=states.append));
    result = interp.execute("CURSOR OFF; PAUSE .25; CURSOR BLOCK", interactive=True);
    assert isinstance(result, DelayRequest) or isinstance(result, BatchResult);
    delay = result if isinstance(result, DelayRequest) else next(item for item in result.results if isinstance(item, DelayRequest));
    assert abs(delay.seconds - .25) < 1e-9;
    assert delay.remaining == ["CURSOR BLOCK"];
    assert interp.evaluate("CURSOR()") == 0;
    interp.execute_remaining(delay.remaining, interactive=True);
    assert interp.evaluate("CURSOR()") == 2;
    delay2 = interp.execute("DELAY .1", interactive=False);
    assert isinstance(delay2, DelayRequest) and abs(delay2.seconds - .1) < 1e-9;
