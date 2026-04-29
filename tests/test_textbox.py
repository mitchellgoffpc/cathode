"""Tests for the cathode.textbox editable text widget."""
from unittest.mock import Mock

import pytest

from cathode.components import Box, Text
from cathode.layout import layout
from cathode.render import render
from cathode.styles import Styles, Wrap
from cathode.textbox import TextBox, TextBoxController
from cathode.tree import ElementTree, mount, update


def create_tree(textbox: TextBox) -> tuple[ElementTree, Box, TextBoxController]:
    root = Box()[textbox]
    tree = ElementTree(root)
    mount(tree, root)
    assert isinstance(textbox.controller, TextBoxController)
    return tree, root, textbox.controller


@pytest.mark.parametrize(("text", "cursor_pos", "width", "wrap", "expected_text"), [
    pytest.param("", 0, 10, Wrap.EXACT, Styles.inverse(' '), id="empty text"),
    pytest.param("Hello", 0, 10, Wrap.EXACT, Styles.inverse('H') + "ello", id="cursor at start"),
    pytest.param("Hello", 2, 10, Wrap.EXACT, "He" + Styles.inverse('l') + "lo", id="cursor in middle"),
    pytest.param("Hello", 5, 10, Wrap.EXACT, "Hello" + Styles.inverse(' '), id="cursor at end"),
    pytest.param("12345", 5, 5, Wrap.EXACT, "12345\n" + Styles.inverse(' '), id="exact wrap at width boundary"),
    pytest.param("1234567890", 5, 5, Wrap.EXACT, "12345\n" + Styles.inverse('6') + "7890",
                 id="exact wrap cursor at line end"),
    pytest.param("1234567890", 7, 5, Wrap.EXACT, "12345\n67" + Styles.inverse('8') + "90",
                 id="exact wrap cursor in second line"),
    pytest.param("123\n456", 4, 10, Wrap.EXACT, "123 \n" + Styles.inverse('4') + "56", id="exact wrap with newline"),
    pytest.param("Hello", 2, 10, Wrap.WORDS, "He" + Styles.inverse('l') + "lo", id="word wrap no break needed"),
    pytest.param("Hello World", 6, 6, Wrap.WORDS, "Hello \n" + Styles.inverse('W') + "orld", id="word wrap at space"),
    pytest.param("Hello World", 5, 6, Wrap.WORDS, "Hello" + Styles.inverse(' ') + "\nWorld",
                 id="word wrap at space + cursor"),
    pytest.param("At the ball", 6, 6, Wrap.WORDS, "At \nthe" + Styles.inverse(' ') + "\nball",
                 id="word wrap at cursor before space"),
    pytest.param("Hello    ", 8, 6, Wrap.WORDS, "Hello" + Styles.inverse(' '), id="word wrap, cursor past end"),
    pytest.param("Supercalifragilistic", 10, 10, Wrap.WORDS,
                 "Supercali\nf" + Styles.inverse('r') + "agilist\nic", id="word wrap long word breaks"),
    pytest.param("Hello\nWorld", 6, 10, Wrap.EXACT, "Hello \n" + Styles.inverse('W') + "orld",
                 id="cursor right after newline"),
    pytest.param("123456789", 9, 5, Wrap.EXACT, "12345\n6789" + Styles.inverse(' '),
                 id="exact wrap multiple lines cursor end"),
    pytest.param("Hi       World", 5, 6, Wrap.WORDS, "Hi   " + Styles.inverse(' ') + "\nWorld",
                 id="word wrap trailing spaces"),
    pytest.param("Hi       World", 7, 6, Wrap.WORDS, "Hi   " + Styles.inverse(' ') + "\nWorld",
                 id="word wrap trailing spaces, cursor past end"),
])
def test_textbox_wrapping_rendering(text: str, cursor_pos: int, width: int, wrap: Wrap, expected_text: str) -> None:
    textbox = TextBoxController(TextBox(width=width, wrap=wrap))
    textbox.text = text
    textbox.cursor_pos = cursor_pos
    text_elem = textbox.contents()[0]
    assert isinstance(text_elem, Text)
    assert text_elem.wrapped(width) == expected_text

def test_textbox_width_limit() -> None:
    tree, root, textbox = create_tree(TextBox(width=1.0, wrap=Wrap.WORDS))
    textbox.text = "123456789     "
    textbox.cursor_pos = 12
    update(tree, textbox.props)
    layout(tree, root, available_width=10)
    assert render(tree, root) == '123456789' + Styles.inverse(' ')


@pytest.mark.parametrize(("initial_text", "initial_cursor", "inputs", "expected_text", "expected_cursor"), [
    pytest.param("", 0, ["A", "B"], "AB", 2, id="insert at end"),
    pytest.param("AB", 1, ["X"], "AXB", 2, id="insert in middle"),
    pytest.param("Hello", 5, ["\x7f"], "Hell", 4, id="backspace at end"),
    pytest.param("Hello", 2, ["\x7f"], "Hllo", 1, id="backspace in middle"),
    pytest.param("Hello", 0, ["\x7f"], "Hello", 0, id="backspace at start"),
    pytest.param("Hi Hello World", 14, ["\x1b\x7f"], "Hi Hello ", 9, id="backspace word (Alt+Backspace)"),
    pytest.param("Hello", 2, ["\x04"], "Helo", 2, id="delete character at cursor (Ctrl+D)"),
    pytest.param("Hello", 5, ["\x04"], "Hello", 5, id="delete at end (Ctrl+D)"),
    pytest.param("Hi Hello World", 2, ["\x1bd"], "Hi World", 2, id="delete word (Alt+D)"),
    pytest.param("Hello", 2, ["\x14"], "Hlelo", 3, id="transpose characters (Ctrl+T)"),
    pytest.param("Hello", 5, ["\x14"], "Hello", 5, id="transpose at end no-op (Ctrl+T)"),
    pytest.param("Hello", 2, ["\x0f"], "He\nllo", 2, id="insert newline after cursor (Ctrl+O)"),
    pytest.param("Hello World", 5, ["\x1b\r"], "Hello\n World", 6, id="insert newline at cursor (Alt+Enter)"),
])
def test_textbox_basic_text_editing(initial_text: str, initial_cursor: int, inputs: list[str],
                                     expected_text: str, expected_cursor: int) -> None:
    textbox = TextBoxController(TextBox(width=20))
    textbox.text = initial_text
    textbox.cursor_pos = initial_cursor
    for ch in inputs:
        textbox.handle_input(ch)
    assert textbox.text == expected_text
    assert textbox.cursor_pos == expected_cursor


@pytest.mark.parametrize(("initial_text", "initial_cursor", "inputs", "expected_cursor"), [
    pytest.param("Hello World", 5, ["\x02", "\x1b[D"], 4, id="move backward one character (Ctrl+B / left arrow)"),
    pytest.param("Hello World", 4, ["\x06", "\x1b[C"], 5, id="move forward one character (Ctrl+F / right arrow)"),
    pytest.param("Hello\nWorld\nTest", 0, ["\x0e", "\x1b[B"], 6, id="move to next line (Ctrl+N / down arrow)"),
    pytest.param("Hello\nWorld\nTest", 12, ["\x10", "\x1b[A"], 6, id="move to previous line (Ctrl+P / up arrow)"),
    pytest.param("Hello\nWorld", 8, ["\x01"], 6, id="move to start of line (Ctrl+A)"),
    pytest.param("Hello\nWorld", 2, ["\x05"], 5, id="move to end of line (Ctrl+E)"),
    pytest.param("Hello World Test", 0, ["\x1bf"], 6, id="move forward one word (Alt+F)"),
    pytest.param("Hello World Test", 11, ["\x1bb"], 6, id="move backward one word (Alt+B)"),
    pytest.param("Hello", 0, ["\x02", "\x1b[D"], 0, id="move back at start no-op"),
    pytest.param("Hello", 5, ["\x06", "\x1b[C"], 5, id="move forward at end no-op"),
    pytest.param("Hello\nWorld", 0, ["\x01"], 0, id="move to start at start no-op"),
    pytest.param("Hello\nWorld", 11, ["\x05"], 11, id="move to end at end no-op"),
])
def test_textbox_navigation_keybindings(initial_text: str, initial_cursor: int,
                                         inputs: list[str], expected_cursor: int) -> None:
    for ch in inputs:
        tree, root, textbox = create_tree(TextBox(width=20))
        textbox.text = initial_text
        textbox.cursor_pos = initial_cursor
        layout(tree, root)
        textbox.handle_input(ch)
        assert textbox.text == initial_text
        assert textbox.cursor_pos == expected_cursor


@pytest.mark.parametrize(("initial_text", "initial_cursor", "ch", "expected_cursor"), [
    pytest.param("hello world foo", 0, "\x1b[B", 6, id="down from line 0 to wrapped line 1"),
    pytest.param("hello world foo", 6, "\x1b[A", 0, id="up from start of wrapped line 1 to line 0"),
    pytest.param("hello world foo", 8, "\x1b[A", 2, id="up preserves column across wrap"),
    pytest.param("supercalifragilistic", 3, "\x1b[B", 12, id="down preserves column across long-word break"),
    pytest.param("supercalifragilistic", 11, "\x1b[A", 2, id="up preserves column across long-word break"),
])
def test_textbox_navigation_across_wrapped_lines(initial_text: str, initial_cursor: int,
                                                  ch: str, expected_cursor: int) -> None:
    tree, root, textbox = create_tree(TextBox(width=10, wrap=Wrap.WORDS))
    textbox.text = initial_text
    textbox.cursor_pos = initial_cursor
    layout(tree, root)
    textbox.handle_input(ch)
    assert textbox.cursor_pos == expected_cursor


@pytest.mark.parametrize(("initial_text", "initial_cursor", "inputs",
                          "expected_text", "expected_cursor", "history", "history_idx"), [
    pytest.param("first", 5, ["\x1b[5~", "\x0e", "\x1b[B"], "second", 6,
                 ["first", "second", "third"], 0, id="move to newer history entry (page down)"),
    pytest.param("third", 5, ["\x1b[6~", "\x10", "\x1b[A"], "second", 6,
                 ["first", "second", "third"], 2, id="move to older history entry (page up)"),
    pytest.param("first", 5, ["\x1b[6~"], "first", 5,
                 ["first", "second", "third"], 0, id="page up at oldest entry no-op"),
    pytest.param("third", 5, ["\x1b[5~"], "third", 5,
                 ["first", "second", "third"], 2, id="page down at newest entry no-op"),
    pytest.param("line1\nline2\nline3", 12, ["\x10", "\x1b[A"], "line1\nline2\nline3", 6,
                 ["first", "second"], 1, id="move to previous line no page up"),
    pytest.param("line1\nline2\nline3", 0, ["\x0e", "\x1b[B"], "line1\nline2\nline3", 6,
                 ["first", "second"], 0, id="move to next line no page down"),
])
def test_textbox_history_paging_keybindings(initial_text: str, initial_cursor: int, inputs: list[str],
                                             expected_text: str, expected_cursor: int,
                                             history: list[str], history_idx: int) -> None:
    for ch in inputs:
        tree, root, textbox = create_tree(TextBox(width=20))
        textbox.text = initial_text
        textbox.cursor_pos = initial_cursor
        textbox.history = history
        textbox.history_idx = history_idx
        layout(tree, root)
        textbox.handle_input(ch)
        assert textbox.text == expected_text
        assert textbox.cursor_pos == expected_cursor


@pytest.mark.parametrize(("initial_text", "initial_cursor", "inputs", "expected_text", "expected_cursor",
                          "mark", "expected_mark", "kill_buf", "expected_kill_buf"), [
    pytest.param("Hello", 2, "\x00", "Hello", 2, None, 2, None, None, id="set mark (Ctrl+Space)"),
    pytest.param("Hello", 2, "\x07", "Hello", 2, 1, None, None, None, id="unset mark (Ctrl+G)"),
    pytest.param("Hello World", 5, "\x0b", "Hello", 5, None, None, None, " World", id="kill to end of line (Ctrl+K)"),
    pytest.param("Hello", 4, "\x17", "Ho", 1, 1, None, None, "ell", id="kill region (Ctrl+W)"),
    pytest.param("Ho", 1, "\x19", "Hello", 4, None, None, "ell", None, id="yank (Ctrl+Y)"),
])
def test_textbox_kill_yank_and_mark_keybindings(initial_text: str, initial_cursor: int, inputs: str,
                                                  expected_text: str, expected_cursor: int,
                                                  mark: int | None, expected_mark: int | None,
                                                  kill_buf: str | None, expected_kill_buf: str | None) -> None:
    textbox = TextBoxController(TextBox(width=20))
    textbox.text = initial_text
    textbox.cursor_pos = initial_cursor
    if mark is not None:
        textbox.mark = mark
    if kill_buf is not None:
        textbox.kill_buffer = kill_buf
    textbox.handle_input(inputs)
    assert textbox.text == expected_text
    assert textbox.cursor_pos == expected_cursor
    if expected_mark is not None:
        assert textbox.mark == expected_mark
    if expected_kill_buf is not None:
        assert textbox.kill_buffer == expected_kill_buf


def test_textbox_placeholder_rendering() -> None:
    textbox = TextBoxController(TextBox(width=20, placeholder='Type here'))
    text_elem = textbox.contents()[0]
    assert isinstance(text_elem, Text)
    assert text_elem.text == Styles.inverse('T') + Styles.dim('ype here')

    textbox.text = 'a'
    text_elem = textbox.contents()[0]
    assert isinstance(text_elem, Text)
    assert text_elem.text == Styles.inverse('a')

def test_textbox_change_callback() -> None:
    handle_change = Mock()
    textbox = TextBoxController(TextBox(width=20, handle_change=handle_change))

    textbox.handle_input('H')
    handle_change.assert_called_once_with('H')
    handle_change.reset_mock()

    textbox.handle_input('\x7f')
    handle_change.assert_called_once_with('')
    handle_change.reset_mock()

    textbox.text = ''
    textbox.cursor_pos = 0
    handle_change.reset_mock()
    textbox.handle_input('\x7f')
    handle_change.assert_not_called()

def test_textbox_bracketed_paste() -> None:
    handle_submit = Mock(return_value=True)
    textbox = TextBoxController(TextBox(width=20, handle_submit=handle_submit))
    textbox.handle_input('\x1b[200~line one\rline two\nline three\x1b[201~')
    assert textbox.text == 'line one\nline two\nline three'
    assert textbox.cursor_pos == len(textbox.text)
    handle_submit.assert_not_called()

def test_textbox_enter_and_submit_handling() -> None:
    handle_submit = Mock(return_value=True)
    textbox = TextBoxController(TextBox(width=20, handle_submit=handle_submit))
    textbox.text = 'Test content'

    textbox.handle_input('\r')
    handle_submit.assert_called_once_with('Test content')
    assert textbox.text == ''
    assert textbox.cursor_pos == 0
    assert textbox.history[-2:] == ['Test content', '']

    handle_submit.return_value = False
    textbox.text = 'Another'
    textbox.handle_input('\r')
    assert textbox.text == 'Another'
