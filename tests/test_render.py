"""Tests for cathode.render output, including borders, spacing, and styled text."""
import time
import unittest

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

class TestInputHandling(unittest.TestCase):
    """Tests for parsing terminal input sequences."""

    def test_split_input_sequence(self) -> None:
        test_cases = [
            ("hello", ["hello"]),
            ("ab\x03cd", ["ab", "\x03", "cd"]),
            ("\x01\x02", ["\x01", "\x02"]),
            ("\x1b[A", ["\x1b[A"]),
            ("hi\x1b[5~there", ["hi", "\x1b[5~", "there"]),
            ("x\x1by", ["x", "\x1by"]),
            ("a\x1b[12;34Bz", ["a", "\x1b[12;34B", "z"]),
            ("a\nb", ["a", "\n", "b"]),
            ("\x7f\x7f\x7f", ["\x7f", "\x7f", "\x7f"]),
        ]
        for sequence, expected in test_cases:
            with self.subTest(sequence=sequence):
                assert _split_input_sequence(sequence) == expected


class TestRender(unittest.TestCase):
    """Tests for the basic render output of boxes and text."""

    def test_empty_box(self) -> None:
        box = Box()[Box(), Text("Hello")]
        assert render_once(box) == "Hello"

    def test_render_styled_text(self) -> None:
        text = Text(f"{Colors.WHITE}this is one line\nthis is another line{Colors.END}")
        expected = f"{Colors.WHITE}this is one line{Colors.END}    \n{Colors.WHITE}this is another line{Colors.END}"
        assert render_once(text) == expected

    def test_width_types(self) -> None:
        test_cases: list[tuple[str, int | None, list]] = [
            ("fixed width", 20, [('Left', 8, 8), ('Right', 8, 8)]),
            ("fractional width", 20, [('Left', 0.3, 6), ('Right', 0.7, 14)]),
            ("auto width", None, [('Hello', None, 5), ('World', None, 5)]),
            ("mixed width types", 30, [('Fixed', 10, 10), ('Fraction', 0.625, 10), ('Auto', None, 4)]),
        ]
        for description, width, _children in test_cases:
            with self.subTest(description=description):
                box = Box(width=width, flex=Axis.HORIZONTAL)[(Text(text, width=width) for text, width, _ in _children)]
                expected_box_width = width or sum(expected_width for _, _, expected_width in _children)
                joined = ''.join(f'{text:<{expected_width}}' for text, _, expected_width in _children)
                expected_result = joined.ljust(expected_box_width)
                assert render_once(box) == expected_result

    def test_layout_width_constraint(self) -> None:
        text = Text("Very long text that should be wrapped", width=10)
        assert render_once(text) == "Very long \ntext that \nshould be \nwrapped   "

    def test_parent_width_constraint(self) -> None:
        box = Box()[Box(width=10)[Text("Very long text that should be wrapped")]]
        assert render_once(box) == "Very long \ntext that \nshould be \nwrapped   "

    def test_mixed_flex_components(self) -> None:
        outer = Box(flex=Axis.HORIZONTAL)[Box(flex=Axis.VERTICAL)[Text("Top"), Text("Bottom")], Text("Side")]
        assert render_once(outer) == "Top   Side\nBottom    "

    def test_horizontal_children_clip_to_constrained_height(self) -> None:
        outer = Box(flex=Axis.HORIZONTAL, height=2)[Text("a\nb\nc"), Text("x")]
        assert render_once(outer) == "ax\nb "


class TestRenderMargin(unittest.TestCase):
    """Tests for margin rendering around elements."""

    def test_margin(self) -> None:
        test_cases: list[tuple[str, str, Spacing, str]] = [
            ("no margin", "Hello", 0, "Hello"),
            ("uniform margin", "Hello", 1, "       \n Hello \n       "),
            ("asymmetric margin", "Hi", {'top': 2, 'bottom': 0, 'left': 3, 'right': 1}, "      \n      \n   Hi "),
            ("multiline with margin", "Line1\nLine2", {'top': 1, 'bottom': 1, 'left': 2, 'right': 2},
                "         \n  Line1  \n  Line2  \n         "),
        ]
        for description, text_content, margin, expected in test_cases:
            with self.subTest(description=description):
                text = Text(text_content, margin=margin)
                assert render_once(text) == expected


class TestRenderBorder(unittest.TestCase):
    """Tests for border drawing on selected sides of elements."""

    def test_border(self) -> None:
        test_cases: list[tuple[str, str, tuple[Side, ...], int, str]] = [
            ("no border", "Hello", (), 0, "Hello"),
            ("full border", "Hi", ('top', 'bottom', 'left', 'right'), 0, "┌──┐\n│Hi│\n└──┘"),
            ("partial border", "Hi", ('top', 'left'), 0, "┌──\n│Hi"),
            ("border with margin", "Hi", ('top', 'bottom', 'left', 'right'), 1,
                "      \n ┌──┐ \n │Hi│ \n └──┘ \n      "),
        ]
        for description, text_content, border, margin, expected in test_cases:
            with self.subTest(description=description):
                text = Text(text_content, margin=margin, border=border, border_style=Borders.SINGLE)
                assert render_once(text) == expected


class TestRenderPerformance(unittest.TestCase):
    """Performance smoke tests for rendering wide and deep trees."""

    def test_render_performance(self) -> None:
        for widget in (WideTree, DeepTree):
            with self.subTest(widget=widget.__name__):
                root = Box()[widget()]
                tree = ElementTree(root)
                mount(tree, root)
                layout(tree, root, 200)

                start = time.perf_counter()
                render(tree, root)
                elapsed = time.perf_counter() - start
                assert elapsed < 0.01, f"Render for {widget.__name__} took {elapsed * 1000:.2f}ms, expected <10ms"
