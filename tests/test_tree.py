"""Tests for cathode.tree element tree mounting, updating, and reconciliation."""
import time
from collections import deque
from collections.abc import Iterator
from dataclasses import dataclass

import pytest

from cathode.components import BaseController, Box, Component, Text, Widget
from cathode.tree import ElementTree, mount, propagate, update
from tests.helpers import DeepTree, WideTree


def toposort(tree: ElementTree) -> Iterator[Component]:
    queue = deque([tree.root.uuid])
    while queue:
        uuid = queue.popleft()
        yield tree.nodes[uuid]
        queue.extend(child.uuid for child in tree.children.get(uuid, []) if child)


@dataclass
class ChildWidget(Widget):
    """Test widget that renders a single text node displaying its `value` prop."""

    value: int

    class Controller(BaseController):
        def contents(self) -> list[Component | None]:
            return [Text(f"Child value: {self.props.value}")]

@dataclass
class ParentWidget(Widget):
    """Test widget that conditionally renders a `ChildWidget` based on controller state."""

    class Controller(BaseController):
        child_value: int | None = 0

        def contents(self) -> list[Component | None]:
            return [Box()[ChildWidget(self.child_value) if self.child_value is not None else None]]


def test_widget_mount_and_update() -> None:
    parent = ParentWidget()
    tree = ElementTree(parent)
    mount(tree, parent)

    _, box, child, text = toposort(tree)
    assert isinstance(box, Box)
    assert isinstance(child, ChildWidget)
    assert isinstance(text, Text)
    assert tree.parents == {box.uuid: parent.uuid, child.uuid: box.uuid, text.uuid: child.uuid}
    assert tree.children == {parent.uuid: [box], box.uuid: [child], child.uuid: [text], text.uuid: []}
    assert text.text == "Child value: 0"

    parent.controller.child_value = 1  # ty: ignore[unresolved-attribute]
    update(tree, parent)

    _, box2, child2, text2 = toposort(tree)
    assert isinstance(text2, Text)
    assert box2.uuid != box.uuid
    assert child2.uuid != child.uuid
    assert text2.uuid != text.uuid
    assert tree.parents == {box2.uuid: parent.uuid, child2.uuid: box2.uuid, text2.uuid: child2.uuid}
    assert tree.children == {parent.uuid: [box2], box2.uuid: [child2], child2.uuid: [text2], text2.uuid: []}
    assert text2.text == "Child value: 1"

    parent.controller.child_value = 1  # ty: ignore[unresolved-attribute]
    update(tree, parent)

    _, box3, child3, text3 = toposort(tree)
    assert box2.uuid != box3.uuid
    assert child3.uuid == child2.uuid
    assert text3.uuid == text2.uuid
    assert tree.parents == {box3.uuid: parent.uuid, child3.uuid: box3.uuid, text3.uuid: child3.uuid}
    assert tree.children == {parent.uuid: [box3], box3.uuid: [child3], child3.uuid: [text3], text3.uuid: []}

    parent.controller.child_value = None  # ty: ignore[unresolved-attribute]
    update(tree, parent)

    _, box4 = toposort(tree)
    assert box3.uuid != box4.uuid
    assert tree.parents == {box4.uuid: parent.uuid}
    assert tree.children == {parent.uuid: [box4], box4.uuid: [None]}


def test_handle_unmount_called_on_removal_and_replacement() -> None:
    unmounted: list[int] = []

    @dataclass
    class Tracked(Widget):
        tag: int

        class Controller(BaseController):
            def handle_unmount(self) -> None:
                unmounted.append(self.props.tag)
                super().handle_unmount()

            def contents(self) -> list[Component | None]:
                return [Text(f"tag {self.props.tag}")]

    @dataclass
    class Host(Widget):
        class Controller(BaseController):
            child: Component | None = Tracked(tag=1)

            def contents(self) -> list[Component | None]:
                return [self.child]

    host = Host()
    tree = ElementTree(host)
    mount(tree, host)

    host.controller.child = Text("now a text")  # ty: ignore[unresolved-attribute]
    update(tree, host)
    assert unmounted == [1]

    host.controller.child = Tracked(tag=2)  # ty: ignore[unresolved-attribute]
    update(tree, host)

    host.controller.child = None  # ty: ignore[unresolved-attribute]
    update(tree, host)
    assert unmounted == [1, 2]


@pytest.mark.parametrize(("keep_going", "expected"), [(True, [1, 2]), (False, [1])])
def test_handle_input_return_controls_propagation(keep_going: bool, expected: list[int]) -> None:
    seen: list[int] = []

    @dataclass
    class Listener(Widget):
        tag: int
        keep_going: bool = True

        class Controller(BaseController):
            def handle_input(self, ch: str) -> bool:
                seen.append(self.props.tag)
                return self.props.keep_going

            def contents(self) -> list[Component | None]:
                return [Listener(tag=2)] if self.props.tag == 1 else [Text("leaf")]

    root = Listener(tag=1, keep_going=keep_going)
    tree = ElementTree(root)
    mount(tree, root)
    propagate(tree, root, 'x', 'input')
    assert seen == expected


@pytest.mark.parametrize("widget", [WideTree, DeepTree], ids=lambda w: w.__name__)
def test_update_performance(widget: type) -> None:
    root = Box()[widget()]
    tree = ElementTree(root)
    mount(tree, root)

    start = time.perf_counter()
    update(tree, root)
    elapsed = time.perf_counter() - start
    assert elapsed < 0.01, f"Update for {widget.__name__} tree took {elapsed * 1000:.2f}ms, expected <10ms"
