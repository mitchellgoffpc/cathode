"""Component primitives for building cathode UIs, including widgets, boxes, and text elements."""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Generic, Literal, TypeVar, get_args
from uuid import UUID, uuid4

from cathode.styles import Axis, Borders, BorderStyle, Color, Colors, Wrap, wrap_lines

if TYPE_CHECKING:
    from typing_extensions import Self

    from cathode.tree import ElementTree

ComponentType = TypeVar('ComponentType', bound='Widget')
T = TypeVar('T')

Side = Literal['top', 'bottom', 'left', 'right']
Spacing = int | dict[Side, int]
Length = int | float | None

def _get_spacing_dict(spacing: Spacing) -> dict[Side, int]:
    assert isinstance(spacing, (int, dict)), "Spacing must be an int or a dict with side keys"
    return {side: spacing if isinstance(spacing, int) else spacing.get(side, 0) for side in get_args(Side)}


@dataclass
class Component:
    """Base class for everything that can appear in a cathode element tree."""

    uuid: UUID = field(default_factory=uuid4, compare=False, kw_only=True)

    def contents(self) -> list[Component | None]:
        """Return the direct children produced by this component."""
        raise NotImplementedError

@dataclass
class Element(Component):
    """Renderable component with size, spacing, borders, and background styling."""

    width: Length = field(default=None, kw_only=True)
    height: Length = field(default=None, kw_only=True)
    margin: Spacing = field(default=0, kw_only=True)
    padding: Spacing = field(default=0, kw_only=True)
    border: Sequence[Side] = field(default=(), kw_only=True)
    border_style: BorderStyle = field(default_factory=lambda: Borders.ROUND, kw_only=True)
    border_color: Color | None = field(default=None, kw_only=True)
    background_color: Color | None = field(default=None, kw_only=True)
    visible: bool = field(default=True, kw_only=True)
    _tree: ElementTree | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Normalize spacing fields and initialize the children list."""
        self.margins = _get_spacing_dict(self.margin)
        self.paddings = _get_spacing_dict(self.padding)
        self.borders = {side: int(side in self.border) for side in get_args(Side)}
        self.children: list[Component | None] = []

    @property
    def content_width(self) -> int | None:
        """Return the rendered width minus horizontal chrome, or `None` if not yet laid out."""
        if self._tree is None or self.uuid not in self._tree.widths:
            return None
        return max(0, self._tree.widths[self.uuid] - self.chrome(Axis.HORIZONTAL))

    @property
    def content_height(self) -> int | None:
        """Return the rendered height minus vertical chrome, or `None` if not yet laid out."""
        if self._tree is None or self.uuid not in self._tree.heights:
            return None
        return max(0, self._tree.heights[self.uuid] - self.chrome(Axis.VERTICAL))

    def __getitem__(self, args: Component | Iterable[Component | None] | None) -> Self:
        """Assign `args` as the element's children using the `element[child, ...]` syntax."""
        self.children = [args] if isinstance(args, Component) else list(args) if args else []
        return self

    def length(self, axis: Axis) -> Length:
        """Return the configured length (width or height) along `axis`."""
        return self.width if axis is Axis.HORIZONTAL else self.height

    def chrome(self, axis: Axis) -> int:
        """Return the total non-content space (margin, border, padding) consumed along `axis`."""
        a: Side = 'left' if axis is Axis.HORIZONTAL else 'top'
        b: Side = 'right' if axis is Axis.HORIZONTAL else 'bottom'
        return (
            self.paddings[a] + self.paddings[b] + self.margins[a] + self.margins[b] + self.borders[a] + self.borders[b]
        )

    def contents(self) -> list[Component | None]:
        """Return the children assigned to this element."""
        return self.children

@dataclass
class Text(Element):
    """Leaf element that renders a string with optional wrapping."""

    text: str
    wrap: Wrap = field(default=Wrap.WORDS, kw_only=True)
    text_color: Color | None = field(default=None, kw_only=True)

    def __post_init__(self) -> None:
        """Initialize the element and the per-width wrap cache."""
        super().__post_init__()
        self._wrap_cache: dict[int, str] = {}

    def __getitem__(self, args: Component | Iterable[Component | None] | None) -> Self:
        """Disallow assigning children to a leaf `Text` element."""
        raise ValueError(f'{self.__class__.__name__} component is a leaf node and cannot have children')

    def wrapped(self, width: int) -> str:
        """Return the text wrapped to `width` columns, caching the result."""
        if width not in self._wrap_cache:
            text = Colors.apply(self.text, self.text_color) if self.text_color is not None else self.text
            self._wrap_cache[width] = wrap_lines(text.replace('\t', ' ' * 8), width, wrap=self.wrap)
        return self._wrap_cache[width]

@dataclass
class Box(Element):
    """Container element that lays out its children along a horizontal or vertical axis."""

    flex: Axis = Axis.VERTICAL

@dataclass
class Widget(Component):
    """Stateful component whose contents and behavior are driven by an associated controller."""

    Controller: ClassVar[type[BaseController]]
    _controller: BaseController | None = field(default=None, kw_only=True, compare=False)

    @property
    def controller(self) -> BaseController:
        """Return the controller instance bound to this widget."""
        assert self._controller is not None, "Widget's controller instance is not initialized"
        return self._controller

    @controller.setter
    def controller(self, value: BaseController | None) -> None:
        self._controller = value

    def contents(self) -> list[Component | None]:
        """Return the children produced by this widget's controller."""
        return self.controller.contents()


class _StateField(Generic[T]):
    def __init__(self, default: T) -> None:
        self.default = default

    def __set_name__(self, owner: type, name: str) -> None:
        self.attr = f'_state_{name}'

    def __get__(self, instance: Any, owner: type | None = None) -> T:
        if instance is None:
            return self  # ty: ignore[invalid-return-type]
        return getattr(instance, self.attr, self.default)

    def __set__(self, instance: Any, value: T) -> None:
        setattr(instance, self.attr, value)
        instance.set_dirty()


def State(default: T) -> T:
    """Declare a reactive controller field; assigning to it marks the controller dirty."""
    return _StateField(default)  # ty: ignore[invalid-return-type]


class BaseController(Generic[ComponentType]):
    """Base class for widget controllers; subclasses declare state via `State` and produce child components."""

    tree: ElementTree | None = None

    def __init_subclass__(cls: type[BaseController[ComponentType]], *args: Any, **kwargs: Any) -> None:
        """Auto-register this controller on the parameterized `Widget` subclass when subclassed."""
        super().__init_subclass__(*args, **kwargs)
        for base in getattr(cls, '__orig_bases__', []):
            for arg in get_args(base):
                if isinstance(arg, type) and issubclass(arg, Widget) and not hasattr(arg, 'Controller'):
                    arg.Controller = cls
                    return

    def __init__(self, props: ComponentType) -> None:
        """Initialize the controller with the widget `props` it manages."""
        self.props = props

    @property
    def mounted(self) -> bool:
        """Return whether this controller is currently mounted into an element tree."""
        return self.tree is not None

    def set_dirty(self) -> None:
        """Mark this controller's widget as needing re-rendering on the next update pass."""
        if self.tree:
            self.tree.dirty.add(self.props.uuid)

    def handle_mount(self, tree: ElementTree) -> None:
        """Hook called when the widget is first mounted into `tree`."""
        self.tree = tree

    def handle_unmount(self) -> None:
        """Hook called when the widget is removed from its tree."""
        self.tree = None

    def handle_update(self, new_props: ComponentType) -> None:
        """Hook called when the widget's props change."""
        self.props = new_props

    def handle_input(self, ch: str) -> None:
        """Hook called for each input sequence delivered to the widget."""

    def contents(self) -> list[Component | None]:
        """Return the children rendered by this controller."""
        raise NotImplementedError
