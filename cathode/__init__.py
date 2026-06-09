"""cathode is a Python terminal UI library for building interactive CLI tools."""
from cathode.components import BaseController, Box, Component, Element, Overlay, State, Text, Widget
from cathode.keys import Keys
from cathode.render import run
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
    Overlay = Overlay
    Widget = Widget
    Controller = BaseController
    State = staticmethod(State)
    TextBox = TextBox

__all__ = [
    'UI', 'ElementTree', 'Component', 'Element', 'Text', 'Box',
    'Overlay', 'Widget', 'BaseController', 'State', 'TextBox',
    'Axis', 'Borders', 'Colors', 'Keys', 'Styles', 'ansi_len', 'ansi_slice', 'wrap_lines',
    'terminal_bg_color', 'terminal_fg_color',
    'run',
]
