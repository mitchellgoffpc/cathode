"""Tests for cathode.render output, including borders, spacing, and styled text."""
import time

import pytest

from cathode.components import Box, Side, Spacing, Text
from cathode.layout import layout
from cathode.render import _split_input_sequence, render
from cathode.styles import Axis, Borders, Colors
from cathode.tree import ElementTree, mount
from tests.helpers import DeepTree, WideTree


def render_once(element: Box | Text, max_width: int = 100) -> str:
    tree = ElementTree(element)
    mount(tree, element)
    layout(tree, element, max_width)
    return render(tree, element)


@pytest.mark.parametrize(("sequence", "expected"), [
    pytest.param("hello", ["hello"], id="plain text"),
    pytest.param("ab\x03cd", ["ab", "\x03", "cd"], id="control char between text"),
    pytest.param("\x01\x02", ["\x01", "\x02"], id="adjacent control chars split"),
    pytest.param("\x1b[A", ["\x1b[A"], id="lone CSI sequence"),
    pytest.param("hi\x1b[5~there", ["hi", "\x1b[5~", "there"], id="CSI tilde sequence between text"),
    pytest.param("x\x1by", ["x", "\x1by"], id="ESC + non-CSI char (Alt-key)"),
    pytest.param("a\x1bOPb", ["a", "\x1bOP", "b"], id="SS3 function key between text"),
    pytest.param("\x1bOA\x1bOF", ["\x1b[A", "\x1b[F"], id="SS3 cursor keys normalized to CSI"),
    pytest.param("a\x1b[12;34Bz", ["a", "\x1b[12;34B", "z"], id="parameterized CSI sequence"),
    pytest.param("a\nb", ["a", "\n", "b"], id="newline split as control char"),
    pytest.param("\x7f\x7f\x7f", ["\x7f", "\x7f", "\x7f"], id="DEL bytes split individually"),
    pytest.param("a\x1b[200~hi\nthere\rfoo\x1b[201~b", ["a", "\x1b[200~hi\nthere\rfoo\x1b[201~", "b"],
                 id="bracketed paste keeps newlines and CRs intact"),
    pytest.param("\x1b[200~hi\nthere", ["\x1b[200~hi\nthere"],
                 id="unterminated bracketed paste consumes rest of input"),
])
def test_split_input_sequence(sequence: str, expected: list[str]) -> None:
    assert _split_input_sequence(sequence) == expected


def test_empty_box() -> None:
    box = Box()[Box(), Text("Hello")]
    assert render_once(box) == "Hello"

def test_render_styled_text() -> None:
    text = Text(f"{Colors.WHITE}this is one line\nthis is another line{Colors.END}")
    expected = f"{Colors.WHITE}this is one line{Colors.END}    \n{Colors.WHITE}this is another line{Colors.END}"
    assert render_once(text) == expected


@pytest.mark.parametrize(("width", "children"), [
    pytest.param(20, [('Left', 8, 8), ('Right', 8, 8)], id="fixed width"),
    pytest.param(20, [('Left', 0.3, 6), ('Right', 0.7, 14)], id="fractional width"),
    pytest.param(None, [('Hello', None, 5), ('World', None, 5)], id="auto width"),
    pytest.param(30, [('Fixed', 10, 10), ('Fraction', 0.625, 10), ('Auto', None, 4)], id="mixed width types"),
])
def test_width_types(width: int | None, children: list) -> None:
    box = Box(width=width, flex=Axis.HORIZONTAL)[(Text(text, width=w) for text, w, _ in children)]
    expected_box_width = width or sum(expected_width for _, _, expected_width in children)
    joined = ''.join(f'{text:<{expected_width}}' for text, _, expected_width in children)
    expected_result = joined.ljust(expected_box_width)
    assert render_once(box) == expected_result

def test_layout_width_constraint() -> None:
    text = Text("Very long text that should be wrapped", width=10)
    assert render_once(text) == "Very long \ntext that \nshould be \nwrapped   "

def test_parent_width_constraint() -> None:
    box = Box()[Box(width=10)[Text("Very long text that should be wrapped")]]
    assert render_once(box) == "Very long \ntext that \nshould be \nwrapped   "

def test_mixed_flex_components() -> None:
    outer = Box(flex=Axis.HORIZONTAL)[Box(flex=Axis.VERTICAL)[Text("Top"), Text("Bottom")], Text("Side")]
    assert render_once(outer) == "Top   Side\nBottom    "

def test_horizontal_children_clip_to_constrained_height() -> None:
    outer = Box(flex=Axis.HORIZONTAL, height=2)[Text("a\nb\nc"), Text("x")]
    assert render_once(outer) == "ax\nb "


@pytest.mark.parametrize(("text_content", "margin", "expected"), [
    pytest.param("Hello", 0, "Hello", id="no margin"),
    pytest.param("Hello", 1, "       \n Hello \n       ", id="uniform margin"),
    pytest.param("Hi", {'top': 2, 'bottom': 0, 'left': 3, 'right': 1},
                 "      \n      \n   Hi ", id="asymmetric margin"),
    pytest.param("Line1\nLine2", {'top': 1, 'bottom': 1, 'left': 2, 'right': 2},
                 "         \n  Line1  \n  Line2  \n         ", id="multiline with margin"),
])
def test_margin(text_content: str, margin: Spacing, expected: str) -> None:
    text = Text(text_content, margin=margin)
    assert render_once(text) == expected


@pytest.mark.parametrize(("text_content", "border", "margin", "expected"), [
    pytest.param("Hello", (), 0, "Hello", id="no border"),
    pytest.param("Hi", ('top', 'bottom', 'left', 'right'), 0, "┌──┐\n│Hi│\n└──┘", id="full border"),
    pytest.param("Hi", ('top', 'left'), 0, "┌──\n│Hi", id="partial border"),
    pytest.param("Hi", ('top', 'bottom', 'left', 'right'), 1,
                 "      \n ┌──┐ \n │Hi│ \n └──┘ \n      ", id="border with margin"),
])
def test_border(text_content: str, border: tuple[Side, ...], margin: int, expected: str) -> None:
    text = Text(text_content, margin=margin, border=border, border_style=Borders.SINGLE)
    assert render_once(text) == expected


@pytest.mark.parametrize(("text", "tile", "width", "height", "expected"), [
    pytest.param('-', Axis.HORIZONTAL, 5, 1, "-----", id="horizontal fills width"),
    pytest.param('ab', Axis.HORIZONTAL, 5, 1, "ababa", id="horizontal partial repeat"),
    pytest.param('|', Axis.VERTICAL, 1, 3, "|\n|\n|", id="vertical fills height"),
    pytest.param('xy', (Axis.HORIZONTAL, Axis.VERTICAL), 3, 2, "xyx\nxyx", id="both axes fill rectangle"),
    pytest.param('hello world', Axis.VERTICAL, 5, 4, "hello\nworld\nhello\nworld", id="wrap then tile vertically"),
])
def test_tile(text: str, tile: Axis | tuple, width: int, height: int, expected: str) -> None:
    assert render_once(Text(text, tile=tile, width=width, height=height)) == expected

def test_tile_applies_text_color() -> None:
    text = Text('-', tile=Axis.HORIZONTAL, width=3, text_color=Colors.RED)
    assert render_once(text) == f"{Colors.RED}---{Colors.END}"


@pytest.mark.parametrize("widget", [WideTree, DeepTree], ids=lambda w: w.__name__)
def test_render_performance(widget: type) -> None:
    root = Box()[widget()]
    tree = ElementTree(root)
    mount(tree, root)
    layout(tree, root, 200)

    start = time.perf_counter()
    render(tree, root)
    elapsed = time.perf_counter() - start
    assert elapsed < 0.01, f"Render for {widget.__name__} took {elapsed * 1000:.2f}ms, expected <10ms"
