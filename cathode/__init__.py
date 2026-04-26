from cathode.components import BaseController, Box, Component, Element, Text, Widget
from cathode.render import render_root
from cathode.styles import Axis, Borders, Colors, Styles, ansi_len, ansi_slice, wrap_lines
from cathode.termcolor import terminal_bg_color, terminal_fg_color
from cathode.textbox import TextBox
from cathode.tree import ElementTree


class UI:
    """Convenience namespace exposing the core cathode component types under a single import."""

    Component = Component
    Element = Element
    Text = Text
    Box = Box
    Widget = Widget
    Controller = BaseController
    TextBox = TextBox

__all__ = [
    'UI', 'ElementTree', 'Component', 'Element', 'Text', 'Box', 'Widget', 'Controller', 'TextBox',
    'Axis', 'Borders', 'Colors', 'Styles', 'ansi_len', 'ansi_slice', 'wrap_lines',
    'terminal_bg_color', 'terminal_fg_color',
    'render_root',
]
