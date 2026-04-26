"""Shared test helpers and fixtures for the cathode test suite."""
from dataclasses import dataclass

from cathode.components import BaseController, Box, Component, Text, Widget


@dataclass
class WideTree(Widget):
    """Test fixture widget that renders a wide, shallow tree of 100 sibling text nodes."""

    class Controller(BaseController):
        def contents(self) -> list[Component | None]:
            children = (Text(text=str(i), margin={'top': 1, 'left': 1}, border=['bottom', 'right']) for i in range(100))
            return [Box()[children]]

@dataclass
class DeepTree(Widget):
    """Test fixture widget that renders a deeply nested tree of 100 boxes around a single leaf."""

    class Controller(BaseController):
        def contents(self) -> list[Component | None]:
            node: Component = Text(text='leaf', width=1.0)
            for _ in range(100):
                node = Box(margin={'top': 1, 'left': 1}, border=['bottom', 'right'])[node]
            return [node]
