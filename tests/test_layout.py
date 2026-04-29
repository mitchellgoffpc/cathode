"""Tests for cathode.layout sizing and offset computation."""
import time

import pytest

from cathode.components import Box, Text
from cathode.layout import layout
from cathode.styles import Axis, Colors, Wrap
from cathode.tree import ElementTree, mount
from tests.helpers import DeepTree, WideTree


@pytest.mark.parametrize(("flex", "expected_size", "children", "expected_layouts"), [
    pytest.param(Axis.HORIZONTAL, (30, 1), [('A', 10, None), ('B', 20, None)],
                 [(0, 0, 10, 1), (10, 0, 20, 1)], id="h fixed widths"),
    pytest.param(Axis.HORIZONTAL, (10, 1), [('Hello', None, None), ('World', None, None)],
                 [(0, 0, 5, 1), (5, 0, 5, 1)], id="h flexible widths"),
    pytest.param(Axis.HORIZONTAL, (100, 1), [('X', 0.25, None), ('Y', 0.75, None)],
                 [(0, 0, 25, 1), (25, 0, 75, 1)], id="h fractional widths"),
    pytest.param(Axis.HORIZONTAL, (60, 1),
                 [('Fixed', 10, None), ('Flex-12345', None, None), ('Frac', 0.5, None)],
                 [(0, 0, 10, 1), (10, 0, 10, 1), (20, 0, 40, 1)], id="h mixed widths"),
    pytest.param(Axis.HORIZONTAL, (2, 5), [('A', None, 3), ('B', None, 5)],
                 [(0, 0, 1, 3), (1, 0, 1, 5)], id="h fixed heights"),
    pytest.param(Axis.HORIZONTAL, (3, 1), [('A', None, None), ('BB', None, None)],
                 [(0, 0, 1, 1), (1, 0, 2, 1)], id="h flexible heights"),
    pytest.param(Axis.HORIZONTAL, (2, 75), [('X', None, 0.25), ('Y', None, 0.75)],
                 [(0, 0, 1, 25), (1, 0, 1, 75)], id="h fractional heights"),
    pytest.param(Axis.HORIZONTAL, (13, 50),
                 [('Fixed', None, 5), ('Axis', None, None), ('Frac', None, 0.5)],
                 [(0, 0, 5, 5), (5, 0, 4, 1), (9, 0, 4, 50)], id="h mixed heights"),
    pytest.param(Axis.VERTICAL, (20, 2), [('A', 10, None), ('B', 20, None)],
                 [(0, 0, 10, 1), (0, 1, 20, 1)], id="v fixed widths"),
    pytest.param(Axis.VERTICAL, (5, 2), [('Hello', None, None), ('World', None, None)],
                 [(0, 0, 5, 1), (0, 1, 5, 1)], id="v flexible widths"),
    pytest.param(Axis.VERTICAL, (75, 2), [('X', 0.25, None), ('Y', 0.75, None)],
                 [(0, 0, 25, 1), (0, 1, 75, 1)], id="v fractional widths"),
    pytest.param(Axis.VERTICAL, (50, 3),
                 [('Fixed', 5, None), ('Axis', None, None), ('Frac', 0.5, None)],
                 [(0, 0, 5, 1), (0, 1, 4, 1), (0, 2, 50, 1)], id="v mixed widths"),
    pytest.param(Axis.VERTICAL, (1, 8), [('A', None, 3), ('B', None, 5)],
                 [(0, 0, 1, 3), (0, 3, 1, 5)], id="v fixed heights"),
    pytest.param(Axis.VERTICAL, (2, 2), [('A', None, None), ('BB', None, None)],
                 [(0, 0, 1, 1), (0, 1, 2, 1)], id="v flexible heights"),
    pytest.param(Axis.VERTICAL, (1, 100), [('X', None, 0.25), ('Y', None, 0.75)],
                 [(0, 0, 1, 25), (0, 25, 1, 75)], id="v fractional heights"),
    pytest.param(Axis.VERTICAL, (10, 55),
                 [('Fixed', None, 10), ('Flex-12345', None, None), ('Frac', None, 0.5)],
                 [(0, 0, 5, 10), (0, 10, 10, 1), (0, 11, 4, 44)], id="v mixed heights"),
    pytest.param(Axis.HORIZONTAL, (0, 0), [('', None, None)], [(0, 0, 0, 0)], id="empty child"),
    pytest.param(Axis.HORIZONTAL, (20, 2), [('This text is longer than twenty chars', 20, None)],
                 [(0, 0, 20, 2)], id="text width constraint"),
])
def test_flex_layout(flex: Axis, expected_size: tuple[int, int],
                     children: list[tuple], expected_layouts: list[tuple]) -> None:
    texts = [Text(text, width=w, height=h, wrap=Wrap.EXACT) for text, w, h in children]
    box = Box(flex=flex)[texts]
    tree = ElementTree(box)
    mount(tree, box)
    layout(tree, box, 100, 100)

    assert (tree.widths[box.uuid], tree.heights[box.uuid]) == expected_size
    for child, (x, y, w, h) in zip(texts, expected_layouts, strict=True):
        assert tree.widths[child.uuid] == w
        assert tree.heights[child.uuid] == h
        assert tree.offsets[child.uuid].x == x
        assert tree.offsets[child.uuid].y == y


@pytest.mark.parametrize(("parent_width", "expected_size", "children", "expected_layouts"), [
    pytest.param(20, (20, 2), [('This text is longer than twenty chars', None, None)],
                 [(0, 0, 20, 2)], id="child text width constraint"),
    pytest.param(20, (20, 1), [('A', 10, None), ('B', 20, None)],
                 [(0, 0, 10, 1), (10, 0, 10, 1)], id="child box width constraint"),
])
def test_flex_layout_with_parent_width(parent_width: int, expected_size: tuple[int, int],
                                        children: list[tuple], expected_layouts: list[tuple]) -> None:
    texts = [Text(text, width=w, height=h, wrap=Wrap.EXACT) for text, w, h in children]
    box = Box(flex=Axis.HORIZONTAL, width=parent_width)[texts]
    tree = ElementTree(box)
    mount(tree, box)
    layout(tree, box, 100, 100)

    assert (tree.widths[box.uuid], tree.heights[box.uuid]) == expected_size
    for child, (x, y, w, h) in zip(texts, expected_layouts, strict=True):
        assert tree.widths[child.uuid] == w
        assert tree.heights[child.uuid] == h
        assert tree.offsets[child.uuid].x == x
        assert tree.offsets[child.uuid].y == y


@pytest.mark.parametrize(("outer_spec", "inner_spec", "text_spec", "expected_outer", "expected_text"), [
    pytest.param((None, None), (None, None), ('A', 10, None), (10, 1), (10, 1), id="fixed width"),
    pytest.param((None, None), (None, None), ('A', None, 3), (1, 3), (1, 3), id="fixed height"),
    pytest.param((None, None), (None, None), ('Hello', 1.0, None), (100, 1), (100, 1), id="fractional width"),
    pytest.param((None, None), (None, None), ('X', None, 0.5), (1, 50), (1, 50), id="fractional height"),
    pytest.param((None, None), (0.5, None), ('Hello', 0.5, None), (50, 1), (25, 1), id="nested fractional width"),
    pytest.param((None, None), (None, 0.5), ('X', None, 0.5), (1, 50), (1, 25), id="nested fractional height"),
    pytest.param((20, None), (None, None), ('Wide', 30, None), (20, 1), (20, 1), id="child width constraint"),
    pytest.param((None, 3), (None, None), ('Tall', None, 5), (4, 3), (4, 3), id="child height constraint"),
])
def test_nested_flex_layout(outer_spec: tuple, inner_spec: tuple, text_spec: tuple,
                            expected_outer: tuple[int, int], expected_text: tuple[int, int]) -> None:
    outer_w, outer_h = outer_spec
    inner_w, inner_h = inner_spec
    text, w, h = text_spec
    text_elem = Text(text, width=w, height=h)
    outer_box = Box(width=outer_w, height=outer_h)[Box(width=inner_w, height=inner_h)[text_elem]]
    tree = ElementTree(outer_box)
    mount(tree, outer_box)
    layout(tree, outer_box, 100, 100)

    assert (tree.widths[outer_box.uuid], tree.heights[outer_box.uuid]) == expected_outer
    assert (tree.widths[text_elem.uuid], tree.heights[text_elem.uuid]) == expected_text


def _make_chrome(m: int, b: int, p: int) -> dict:
    return {'margin': m, 'border': ('top', 'bottom', 'left', 'right') if b else (), 'padding': p}


@pytest.mark.parametrize(("flex", "chrome", "expected_size", "children", "expected_layouts"), [
    pytest.param(Axis.HORIZONTAL, (2, 1, 3), (100, 13), [('A', 1.0, None, (0, 0, 0))],
                 [(6, 6, 88, 1)], id="parent chrome h"),
    pytest.param(Axis.VERTICAL, (2, 1, 3), (13, 100), [('A', None, 1.0, (0, 0, 0))],
                 [(6, 6, 1, 88)], id="parent chrome v"),
    pytest.param(Axis.HORIZONTAL, (0, 0, 0), (40, 13),
                 [('A', 20, None, (2, 1, 3)), ('B', 20, None, (0, 0, 0))],
                 [(0, 0, 20, 13), (20, 0, 20, 1)], id="child chrome h, fixed width"),
    pytest.param(Axis.VERTICAL, (0, 0, 0), (13, 40),
                 [('A', None, 20, (2, 1, 3)), ('B', None, 20, (0, 0, 0))],
                 [(0, 0, 13, 20), (0, 20, 1, 20)], id="child chrome v, fixed height"),
    pytest.param(Axis.HORIZONTAL, (0, 0, 0), (14, 13),
                 [('A', None, None, (2, 1, 3)), ('B', None, None, (0, 0, 0))],
                 [(0, 0, 13, 13), (13, 0, 1, 1)], id="child chrome h, flexible width"),
    pytest.param(Axis.VERTICAL, (0, 0, 0), (13, 14),
                 [('A', None, None, (2, 1, 3)), ('B', None, None, (0, 0, 0))],
                 [(0, 0, 13, 13), (0, 13, 1, 1)], id="child chrome v, flexible height"),
    pytest.param(Axis.HORIZONTAL, (0, 0, 0), (3, 3),
                 [(Colors.hex('A', '#333333'), 3, None, (1, 0, 0))], [(0, 0, 3, 3)], id="child chrome, tight packing"),
])
def test_chrome_layout(flex: Axis, chrome: tuple, expected_size: tuple[int, int],
                       children: list[tuple], expected_layouts: list[tuple]) -> None:
    expected_w, expected_h = expected_size
    texts = [Text(text, width=width, height=height, **_make_chrome(*ch))
             for text, width, height, ch in children]
    box = Box(flex=flex, **_make_chrome(*chrome))[texts]
    tree = ElementTree(box)
    mount(tree, box)
    layout(tree, box, 100, 100)

    assert tree.widths[box.uuid] == expected_w
    assert tree.heights[box.uuid] == expected_h
    for child, (x, y, w, h) in zip(texts, expected_layouts, strict=True):
        assert tree.offsets[child.uuid].x == x
        assert tree.offsets[child.uuid].y == y
        assert tree.widths[child.uuid] == w
        assert tree.heights[child.uuid] == h


@pytest.mark.parametrize("widget", [WideTree, DeepTree], ids=lambda w: w.__name__)
def test_layout_performance(widget: type) -> None:
    root = Box()[widget()]
    tree = ElementTree(root)
    mount(tree, root)

    start = time.perf_counter()
    layout(tree, root, 200)
    elapsed = time.perf_counter() - start
    assert elapsed < 0.01, f"Layout for {widget.__name__} took {elapsed * 1000:.2f}ms, expected <10ms"
