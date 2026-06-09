"""Element tree data structure and reconciliation helpers for mounting and updating components."""
from dataclasses import asdict, is_dataclass
from itertools import zip_longest
from typing import Any, NamedTuple
from uuid import UUID

from cathode.components import Component, Element, Overlay, Text, Widget


class Offset(NamedTuple):
    """Pixel-grid coordinate of an element relative to the render origin."""

    x: int
    y: int

class ElementTree:
    """Mutable tree of mounted components with cached layout, parents, and dirty tracking."""

    def __init__(self, root: Component) -> None:
        """Create an empty tree rooted at `root`."""
        self.root = root
        self.nodes: dict[UUID, Component] = {}
        self.parents: dict[UUID, UUID] = {}
        self.children: dict[UUID, list[Component | None]] = {}
        self.collapsed_children: dict[UUID, list[Element]] = {}
        self.overlays: dict[UUID, list[Overlay]] = {}
        self.offsets: dict[UUID, Offset] = {}
        self.widths: dict[UUID, int] = {}
        self.heights: dict[UUID, int] = {}
        self.dirty: set[UUID] = set()
        self.exiting = False

    def __str__(self) -> str:
        """Return the formatted tree starting at the root."""
        return self.format(self.root.uuid)

    def format(self, uuid: UUID, level: int = 0, verbose: bool = False) -> str:
        """Render a human-readable tree starting at the node with the given `uuid`."""
        def truncate(s: str, n: int) -> str: return s if len(s) <= n else s[:n-3] + '...'
        prefix = '  ' * (max(0, level - 1)) + ('└─' if level > 0 else '')
        match self.nodes[uuid]:
            case Text(text=text): attrs = {'text': text}
            case Widget() as widget if is_dataclass(widget): attrs = asdict(widget)
            case _: attrs = {}
        if uuid in self.offsets and uuid in self.widths and uuid in self.heights:
            attrs = {'w': self.widths[uuid], 'h': self.heights[uuid],
                     'x': self.offsets[uuid].x, 'y': self.offsets[uuid].y} | attrs
        uuid_str = f"{str(uuid).split('-')[0]} → " if verbose else ''
        items = (f'{k}={truncate(repr(v), 100)}' for k, v in attrs.items() if not k.startswith('_'))
        attrs_str = '(' + ', '.join(items) + ')'
        result = f"{prefix}{uuid_str}{self.nodes[uuid].__class__.__name__}{attrs_str if attrs else ''}\n"
        for child in self.children.get(uuid, []):
            if child:
                result += self.format(child.uuid, level + 1, verbose=verbose)
        return result

    def layout(self, uuid: UUID) -> tuple[int, int, int, int]:
        """Return the cached `(width, height, x, y)` layout for the node with the given `uuid`."""
        return self.widths[uuid], self.heights[uuid], self.offsets[uuid].x, self.offsets[uuid].y


# Utility functions

def depth(tree: ElementTree, node: Component) -> int:
    """Return the number of ancestors between `node` and the tree root."""
    depth = 0
    while node is not tree.root:
        node = tree.nodes[tree.parents[node.uuid]]
        depth += 1
    return depth

# Propagate input to a component and its subtree
def propagate(tree: ElementTree, node: Component, value: Any, event_type: str) -> None:
    """Dispatch a `handle_<event_type>` event with `value` to `node` and every widget below it."""
    if isinstance(node, Widget):
        getattr(node.controller, f'handle_{event_type}')(value)
    for child in tree.children.get(node.uuid, []):
        if child:
            propagate(tree, child, value, event_type)

# Add a component and all its children to the tree
def mount(tree: ElementTree, component: Component) -> None:
    """Insert `component` and its subtree into `tree`, instantiating widget controllers along the way."""
    if isinstance(component, Widget):
        component.controller = component.Controller(component)
        component.controller.handle_mount(tree)
    elif isinstance(component, Element):
        component._tree = tree  # noqa: SLF001
    tree.nodes[component.uuid] = component
    contents = component.contents()
    tree.children[component.uuid] = contents
    for child in contents:
        if child:
            mount(tree, child)
            tree.parents[child.uuid] = component.uuid

# Remove a component and all its children from the tree
def _unmount(tree: ElementTree, component: Component) -> None:
    for child in tree.children[component.uuid]:
        if child:
            _unmount(tree, child)
    del tree.nodes[component.uuid], tree.children[component.uuid], tree.parents[component.uuid]
    tree.collapsed_children.pop(component.uuid, None)
    tree.overlays.pop(component.uuid, None)
    tree.offsets.pop(component.uuid, None)
    tree.widths.pop(component.uuid, None)
    tree.heights.pop(component.uuid, None)
    if isinstance(component, Widget):
        component.controller.handle_unmount()
        component.controller = None
    elif isinstance(component, Element):
        component._tree = None  # noqa: SLF001

# Update a component's subtree
def update(tree: ElementTree, component: Component) -> None:
    """Reconcile `component`'s subtree against its current `contents()`, mounting and unmounting children."""
    uuid = component.uuid
    new_contents = component.contents()
    old_contents = tree.children[uuid]

    for i, (old_child, new_child) in enumerate(zip_longest(old_contents, new_contents, fillvalue=None)):
        if not old_child and not new_child:
            continue
        elif new_child and not old_child:
            # New child added
            if i >= len(tree.children[uuid]):
                tree.children[uuid].append(new_child)
            else:
                tree.children[uuid][i] = new_child
            mount(tree, new_child)
            tree.parents[new_child.uuid] = uuid
        elif old_child and not new_child:
            # Child removed
            _unmount(tree, old_child)
            tree.children[uuid][i] = None
        elif old_child and new_child and type(old_child) is not type(new_child):
            # Class changed, replace the child
            assert tree.parents[old_child.uuid] == uuid
            _unmount(tree, old_child)
            mount(tree, new_child)
            tree.parents[new_child.uuid] = uuid
            tree.children[uuid][i] = new_child
        elif old_child and new_child and type(old_child) is type(new_child):
            # Class is the same, update recursively
            if isinstance(old_child, Widget) and isinstance(new_child, Widget):
                if old_child == new_child:
                    continue
                new_child.controller = old_child.controller
                new_child.controller.handle_update(new_child)
            elif isinstance(new_child, Element):
                new_child._tree = tree  # noqa: SLF001
            assert tree.parents[old_child.uuid] == uuid
            del tree.nodes[old_child.uuid]
            tree.nodes[new_child.uuid] = new_child
            tree.parents[new_child.uuid] = tree.parents.pop(old_child.uuid)
            tree.children[new_child.uuid] = tree.children.pop(old_child.uuid)
            tree.collapsed_children.pop(old_child.uuid, None)
            tree.overlays.pop(old_child.uuid, None)
            tree.offsets.pop(old_child.uuid, None)
            tree.widths.pop(old_child.uuid, None)
            tree.heights.pop(old_child.uuid, None)
            for child in tree.children.get(new_child.uuid, []):
                if child:
                    tree.parents[child.uuid] = new_child.uuid
            tree.children[uuid][i] = new_child
            update(tree, new_child)
