"""Tests for overlay positioning, clipping, and ANSI-aware compositing over a background."""
from cathode.components import Box, Overlay, Text
from cathode.layout import layout
from cathode.render import render
from cathode.styles import Axis, Colors
from cathode.tree import ElementTree, mount


def render_once(element: Box | Text, max_width: int = 100) -> str:
    tree = ElementTree(element)
    mount(tree, element)
    layout(tree, element, max_width)
    return render(tree, element)


def test_overlay_anchored_placement() -> None:
    box = Box(width=10, height=3, flex=Axis.HORIZONTAL)[
        Text('..........', width=10),
        Overlay(top=1, left=3, width=4, height=1)[Text('ABCD')],
    ]
    assert render_once(box) == "..........\n   ABCD   \n          "

def test_overlay_centering() -> None:
    box = Box(width=7, height=3)[
        Text('xxxxxxx', width=7),
        Overlay(top=1.0, bottom=1.0, left=1.0, right=1.0, width=3, height=1)[Text('YYY')],
    ]
    assert render_once(box) == "xxxxxxx\n  YYY  \n       "

def test_overlay_stretches_between_fixed_insets() -> None:
    box = Box(width=10, height=1)[Overlay(left=2, right=3, height=1)[Text('z', width=1.0)]]
    assert render_once(box) == "  z       "

def test_overlay_excluded_from_parent_size_and_clipped() -> None:
    box = Box(flex=Axis.HORIZONTAL)[Text('hi'), Overlay(width=50, height=5)[Text('Z')]]
    assert render_once(box) == "Z "

def test_overlay_cancels_and_restores_background_styles() -> None:
    box = Box(width=10, height=1, flex=Axis.HORIZONTAL)[
        Text(f'{Colors.RED}XXXXXXXXXX{Colors.END}', width=10),
        Overlay(left=3, width=4, height=1)[Text('ab')],
    ]
    assert render_once(box) == f"{Colors.RED}XXX{Colors.END}ab  {Colors.RED}XXX{Colors.END}"

def test_overlay_styles_close_at_its_boundary() -> None:
    box = Box(width=8, height=1, flex=Axis.HORIZONTAL)[
        Text('--------', width=8),
        Overlay(left=2, width=3, height=1, background_color=Colors.BG_BLUE)[Text('q')],
    ]
    assert render_once(box) == f"--{Colors.BG_BLUE}q  {Colors.BG_END}---"
