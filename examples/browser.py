"""Two-pane file browser demonstrating cathode's alt-screen rendering."""
from __future__ import annotations

import asyncio
import shutil
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from cathode import Box, Component, Styles, Text, Widget, run
from cathode.components import BaseController, State
from cathode.styles import Axis, Wrap, wrap_lines

PREVIEW_MAX_LINES = 200
ACCENT = '#5fafff'
HEADER_BG = '#262626'

def list_entries(path: Path) -> list[Path]:
    try:
        return sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except OSError:
        return []

def read_preview(path: Path) -> str:
    if path.is_dir():
        return '\n'.join(p.name + ('/' if p.is_dir() else '') for p in list_entries(path)[:PREVIEW_MAX_LINES])
    try:
        text = path.read_text()
    except (UnicodeDecodeError, OSError):
        return Styles.dim('<binary or unreadable file>')
    return '\n'.join(text.splitlines()[:PREVIEW_MAX_LINES])


@dataclass
class FileBrowser(Widget):
    """Directory listing on the left, file or directory preview on the right."""

    class Controller(BaseController):
        cwd: Path = State(Path.cwd().resolve())
        selected: int = State(0)
        scroll: int = State(0)
        preview_scroll: int = State(0)

        def viewport_height(self) -> int:
            return max(1, shutil.get_terminal_size().lines - 2)  # subtract header + footer

        def clamp_scroll(self, count: int) -> None:
            height = self.viewport_height()
            if self.selected < self.scroll:
                self.scroll = self.selected
            elif self.selected >= self.scroll + height:
                self.scroll = self.selected - height + 1
            self.scroll = max(0, min(self.scroll, max(0, count - height)))

        def handle_input(self, ch: str) -> bool:
            entries = list_entries(self.cwd)
            if ch == '\x1b[A' and entries:  # up
                self.selected = max(0, self.selected - 1)
                self.clamp_scroll(len(entries))
                self.preview_scroll = 0
            elif ch == '\x1b[B' and entries:  # down
                self.selected = min(len(entries) - 1, self.selected + 1)
                self.clamp_scroll(len(entries))
                self.preview_scroll = 0
            elif ch in ('\r', '\x1b[C') and entries and entries[self.selected].is_dir():  # enter / right
                self.cwd, self.selected, self.scroll, self.preview_scroll = entries[self.selected], 0, 0, 0
            elif ch in ('\x7f', '\x1b[D') and self.cwd.parent != self.cwd:  # backspace / left
                self.cwd, self.selected, self.scroll, self.preview_scroll = self.cwd.parent, 0, 0, 0
            elif ch == '\x1b[5~':  # page up
                self.preview_scroll = max(0, self.preview_scroll - self.viewport_height())
            elif ch == '\x1b[6~' and entries and self.preview_ref.content_width:
                lines = wrap_lines(read_preview(entries[self.selected]), self.preview_ref.content_width, Wrap.WORDS)
                height = self.viewport_height()
                self.preview_scroll = max(0, min(self.preview_scroll + height, lines.count('\n') + 1 - height))
            elif ch == 'q':
                self.exit()
            return True

        def contents(self) -> list[Component | None]:
            entries = list_entries(self.cwd)
            visible = entries[self.scroll:self.scroll + self.viewport_height()]

            list_lines = []
            for i, p in enumerate(visible, start=self.scroll):
                name = p.name + ('/' if p.is_dir() else '')
                list_lines.append(Styles.inverse(name) if i == self.selected else name)
            list_text = '\n'.join(list_lines) if list_lines else Styles.dim('(empty)')
            preview_text = read_preview(entries[self.selected]) if entries else ''
            width = self.preview_ref.content_width if hasattr(self, 'preview_ref') else None
            if width:
                lines = wrap_lines(preview_text, width, Wrap.WORDS).split('\n')
                height = self.viewport_height()
                scroll = max(0, min(self.preview_scroll, max(0, len(lines) - height)))
                preview_text = '\n'.join(lines[scroll:scroll + height])

            header = Text(text=' ' + str(self.cwd), width=1.0, background_color=HEADER_BG)
            footer = Text(text=Styles.dim(' arrows: navigate   pgup/pgdn: scroll   enter: open   backspace: parent'))
            left = Box(width=0.4, height=1.0, border=['right'], border_color=ACCENT, padding={'left': 1, 'right': 1})[
                Text(text=list_text),
            ]
            self.preview_ref = Text(text=preview_text, width=1.0)
            right = Box(width=0.6, height=1.0, padding={'left': 1, 'right': 1})[self.preview_ref]
            body = Box(flex=Axis.HORIZONTAL, height=1.0)[left, right]
            return [header, body, footer]


async def main() -> None:
    await run(FileBrowser(), fullscreen=True)

if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        asyncio.run(main())
