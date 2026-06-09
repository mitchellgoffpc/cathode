"""Terminal rendering loop, input handling, and the run/render entry points for cathode apps."""
import asyncio
import fcntl
import os
import re
import select
import shutil
import sys
import termios
import tty
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from itertools import zip_longest
from typing import Any

from cathode.components import Box, Component, Element, Overlay, Side, Text
from cathode.cursor import ESC, cursor_up, erase_end_line, erase_line, hide_cursor, paste_end, paste_start, show_cursor
from cathode.layout import layout
from cathode.styles import Axis, BorderStyle, Color, Colors, ansi_len, ansi_slice, color_to_ansi
from cathode.tree import ElementTree, depth, mount, propagate, update

CONTROL_SEQ_RE = re.compile(r'\x1b\[[0-9;]*[A-Za-z~]?|\x1bO.|\x1b.|[\x00-\x1f\x7f]')
SS3_TO_CSI: dict[str, str] = {f'\x1bO{c}': f'\x1b[{c}' for c in 'ABCDHF'}  # application cursor mode keys, in CSI form

DrawFn = Callable[[ElementTree, Element, list[str], os.terminal_size], list[str]]

enter_alternative_screen = f"{ESC}?1049h"
exit_alternative_screen = f"{ESC}?1049l"
enable_bracketed_paste = f"{ESC}?2004h"
disable_bracketed_paste = f"{ESC}?2004l"


# Input parsing
def _split_input_sequence(sequence: str) -> list[str]:
    chunks: list[str] = []
    last = 0
    for match in CONTROL_SEQ_RE.finditer(sequence):
        if match.start() > last:
            chunks.append(sequence[last:match.start()])
        chunk: str = match.group(0)
        chunks.append(SS3_TO_CSI.get(chunk, chunk))
        last = match.end()
    if last < len(sequence):
        chunks.append(sequence[last:])
    return _merge_paste_chunks(chunks)

def _merge_paste_chunks(chunks: list[str]) -> list[str]:
    merged: list[str] = []
    i = 0
    while i < len(chunks):
        if chunks[i] == paste_start:
            j = i + 1
            while j < len(chunks) and chunks[j] != paste_end:
                j += 1
            merged.append(''.join(chunks[i:j + 1]))
            i = j + 1
        else:
            merged.append(chunks[i])
            i += 1
    return merged

# Context manager to set O_NONBLOCK on a file descriptor
@contextmanager
def _nonblocking(fd: int) -> Iterator[None]:
    original_fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    try:
        fcntl.fcntl(fd, fcntl.F_SETFL, original_fl | os.O_NONBLOCK)
        yield
    finally:
        fcntl.fcntl(fd, fcntl.F_SETFL, original_fl)


# Rendering logic

def _apply_spacing(rows: list[str], width: int, spacing: dict[Side, int]) -> list[str]:
    left = ' ' * spacing['left']
    right = ' ' * spacing['right']
    vertical = ' ' * (width + spacing['left'] + spacing['right'])
    return [vertical] * spacing['top'] + [left + row + right for row in rows] + [vertical] * spacing['bottom']

def _apply_borders(
    rows: list[str], width: int, borders: set[Side], border_style: BorderStyle, border_color: Color | None,
) -> list[str]:
    if not borders:
        return rows
    color_code = color_to_ansi(border_color, background=False)
    top_left = border_style.top_left if borders >= {'top', 'left'} else ''
    top_right = border_style.top_right if borders >= {'top', 'right'} else ''
    bottom_left = border_style.bottom_left if borders >= {'bottom', 'left'} else ''
    bottom_right = border_style.bottom_right if borders >= {'bottom', 'right'} else ''
    left_border = Colors.ansi(border_style.left, color_code) if 'left' in borders else ''
    right_border = Colors.ansi(border_style.right, color_code) if 'right' in borders else ''

    result = []
    if 'top' in borders:
        result.append(Colors.ansi(top_left + border_style.top * width + top_right, color_code))
    for row in rows:
        result.append(left_border + row + right_border)
    if 'bottom' in borders:
        result.append(Colors.ansi(bottom_left + border_style.bottom * width + bottom_right, color_code))
    return result

def _apply_chrome(rows: list[str], content_width: int, element: Element) -> list[str]:
    padded_width = content_width + element.paddings['left'] + element.paddings['right']
    bordered_width = padded_width + element.borders['left'] + element.borders['right']
    rows = _apply_spacing(rows, content_width, element.paddings)
    if element.background_color:
        color_code = color_to_ansi(element.background_color, background=True)
        rows = [color_code + row + Colors.BG_END for row in rows]
    border_sides = {k for k, v in element.borders.items() if v}
    rows = _apply_borders(rows, padded_width, border_sides, element.border_style, element.border_color)
    rows = _apply_spacing(rows, bordered_width, element.margins)
    return rows

def _fit_height(rows: list[str], width: int, height: int) -> list[str]:
    return rows[:height] + [' ' * width for _ in range(max(0, height - len(rows)))]

def _tile(pattern: str, width: int) -> str:
    if width <= 0 or not (length := ansi_len(pattern)):
        return ' ' * max(0, width)
    return ansi_slice(pattern * (width // length + 1), 0, width)

def _render(tree: ElementTree, element: Element) -> list[str]:
    content_width = tree.widths[element.uuid] - element.chrome(Axis.HORIZONTAL)
    content_height = tree.heights[element.uuid] - element.chrome(Axis.VERTICAL)

    match element:
        case Text():
            if Axis.HORIZONTAL in element.tiles:
                lines = element.text.split('\n')
                rows = [Colors.apply(_tile(line, content_width), element.text_color) for line in lines]
            else:
                wrapped = element.wrapped(content_width)
                rows = [line + ' ' * (content_width - ansi_len(line)) for line in wrapped.split('\n')]
            if Axis.VERTICAL in element.tiles:
                rows = [rows[i % len(rows)] for i in range(content_height)]
            else:
                rows = _fit_height(rows, content_width, content_height)
        case Box():
            children = tree.collapsed_children[element.uuid]
            child_rows = [_render(tree, child) for child in children]
            child_widths = [tree.widths[child.uuid] for child in children]

            if element.flex is Axis.VERTICAL:
                rows = []
                for crows, cwidth in zip(child_rows, child_widths, strict=True):
                    rows.extend([row + ' ' * (content_width - cwidth) for row in crows])
                rows = _fit_height(rows, content_width, content_height)
            else:
                for crows, cwidth in zip(child_rows, child_widths, strict=True):
                    crows[:] = _fit_height(crows, cwidth, content_height)
                remaining_width = content_width - sum(child_widths)
                child_rows.append([' ' * remaining_width for _ in range(content_height)])
                rows = [''.join(row_parts) for row_parts in zip(*child_rows, strict=True)]
        case _:
            raise ValueError(f"Unknown element type: {type(element)}")

    for overlay in tree.overlays[element.uuid]:
        _composite(tree, rows, content_width, overlay)
    return _apply_chrome(rows, content_width, element)

def _composite(tree: ElementTree, rows: list[str], width: int, overlay: Overlay) -> None:
    x, y = tree.offsets[overlay.uuid]
    for i, overlay_row in enumerate(_render(tree, overlay)):
        if 0 <= y + i < len(rows):
            overlay_width = ansi_len(overlay_row)
            background = rows[y + i]
            rows[y + i] = ansi_slice(background, 0, x) + overlay_row + ansi_slice(background, x + overlay_width, width)

def render(tree: ElementTree, element: Element) -> str:
    """Return the fully rendered string for `element` based on cached layout in `tree`."""
    return '\n'.join(_render(tree, element))


# Terminal session

@contextmanager
def _terminal_session(alt_screen: bool = False, raw: bool = False) -> Iterator[int]:
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    if alt_screen:
        sys.stdout.write(enter_alternative_screen)
    sys.stdout.write(enable_bracketed_paste)
    sys.stdout.flush()
    hide_cursor()
    try:
        if raw:
            tty.setraw(fd)
        else:
            tty.setcbreak(fd)
            mode = termios.tcgetattr(fd)
            mode[0] &= ~(termios.ICRNL | termios.IXON)  # keep Enter as \r and disable Ctrl+S/Q flow control
            termios.tcsetattr(fd, termios.TCSANOW, mode)
        yield fd
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        show_cursor()
        sys.stdout.write(disable_bracketed_paste)
        if alt_screen:
            sys.stdout.write(exit_alternative_screen)
        sys.stdout.flush()


# Draw strategies

def _draw_append(tree: ElementTree, root: Element, prev_lines: list[str], size: os.terminal_size) -> list[str]:
    layout(tree, root, size.columns)
    new_lines = render(tree, root).split('\n')

    if not prev_lines:
        sys.stdout.write('\n\r'.join(new_lines) + '\n')
        sys.stdout.flush()
        return new_lines

    line_drop = len(prev_lines) - len(new_lines)
    if line_drop > min(size.lines / 2, size.lines - 20):
        sys.stdout.write('\033c')
        prev_lines = []

    max_lines = max(len(prev_lines), len(new_lines))
    new_lines = new_lines + [''] * (max_lines - len(new_lines))

    line_diffs = zip_longest(prev_lines, new_lines, fillvalue='')
    first_diff_idx = next((i for i, (prev, new) in enumerate(line_diffs) if prev != new), None)
    if first_diff_idx is None:
        return new_lines

    output = cursor_up(len(prev_lines) - first_diff_idx) if prev_lines else ''
    for prev_line, new_line in zip_longest(prev_lines[first_diff_idx:], new_lines[first_diff_idx:], fillvalue=''):
        sys.stdout.write('\r')
        if ansi_len(new_line) < ansi_len(prev_line):
            output += erase_line
        output += new_line + '\n\r'

    sys.stdout.write(output)
    sys.stdout.flush()
    return new_lines

def _draw_full(tree: ElementTree, root: Element, prev_lines: list[str], size: os.terminal_size) -> list[str]:
    layout(tree, root, size.columns, size.lines)
    new_lines = render(tree, root).split('\n')[:size.lines]
    new_lines = new_lines + [''] * (size.lines - len(new_lines))
    sys.stdout.write('\033[H' + '\n\r'.join(line + erase_end_line for line in new_lines))
    sys.stdout.flush()
    return new_lines

def _finalize_append(prev_lines: list[str]) -> None:
    reversed_lines = enumerate(reversed(prev_lines))
    first_non_blank = next((i for i, line in reversed_lines if line.strip()), len(prev_lines) - 1)
    if first_non_blank > 0:
        sys.stdout.write(cursor_up(first_non_blank))
    sys.stdout.write('\r\n')
    sys.stdout.flush()


# Main render loop

async def _input_loop(tree: ElementTree, root: Element, draw: DrawFn, prev_lines: list[str]) -> None:
    fd = sys.stdin.fileno()
    size = shutil.get_terminal_size()
    prev_lines[:] = draw(tree, root, prev_lines, size)
    while True:
        ready, _, _ = select.select([sys.stdin], [], [], 0.05)
        if ready:
            with _nonblocking(fd):
                sequence = ''
                while (ch := sys.stdin.read(1)):
                    sequence += ch
            for chunk in _split_input_sequence(sequence):
                propagate(tree, root, chunk, 'input')

        new_size = shutil.get_terminal_size()
        resized = new_size != size
        size = new_size
        if resized:
            sys.stdout.write(f'{ESC}2J{ESC}H')
            prev_lines.clear()

        if tree.dirty or resized:
            for uuid in sorted(tree.dirty, key=lambda uuid: depth(tree, tree.nodes[uuid])):  # top-down
                if uuid in tree.nodes:
                    update(tree, tree.nodes[uuid])
            tree.dirty.clear()
            prev_lines[:] = draw(tree, root, prev_lines, size)
        if tree.exiting:
            break
        await asyncio.sleep(0.01)


def _setup(_root: Component) -> tuple[ElementTree, Element]:
    root = _root if isinstance(_root, Element) else Box()[_root]  # Root component needs to be an element
    tree = ElementTree(root)
    mount(tree, root)
    return tree, root


async def run(root: Component, *, fullscreen: bool = False, raw: bool = False) -> Any:
    """Run the interactive render loop, mounting `root` and dispatching input until exit.

    The app draws inline in the terminal's normal scrollback. Pass `fullscreen=True` to render in
    the alternate screen buffer instead.

    By default the terminal is set to cbreak mode, so the kernel still translates Ctrl+C into SIGINT
    and Ctrl+Z into SIGTSTP. Pass `raw=True` to receive those bytes as input instead, e.g. to
    handle them in a root component's `handle_input`.

    Returns:
        The value passed to `BaseController.exit`, or `None`.
    """
    tree, element = _setup(root)
    prev_lines: list[str] = []
    with _terminal_session(alt_screen=fullscreen, raw=raw):
        try:
            await _input_loop(tree, element, _draw_full if fullscreen else _draw_append, prev_lines)
        finally:
            if not fullscreen:
                _finalize_append(prev_lines)
    return tree.exit_result
