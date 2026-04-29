"""Tests for cathode.components reactive state."""
from dataclasses import dataclass

from cathode.components import BaseController, Component, State, Text, Widget
from cathode.tree import ElementTree, mount


def test_state_assignment_marks_tree_dirty() -> None:
    @dataclass
    class Counter(Widget):
        class Controller(BaseController):
            count = State(0)

            def contents(self) -> list[Component | None]:
                return [Text(f"count: {self.count}")]

    widget = Counter()
    tree = ElementTree(widget)
    mount(tree, widget)
    assert tree.dirty == set()

    widget.controller.count = 1  # ty: ignore[unresolved-attribute]
    assert tree.dirty == {widget.uuid}
