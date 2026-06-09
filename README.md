# cathode

cathode is a small Python terminal UI library for building interactive CLI tools. You compose a tree of declarative elements — boxes, text, and stateful widgets — and cathode handles layout, ANSI styling, input dispatch, and efficient redrawing. It targets Python 3.10+ and has no runtime dependencies.

## Installation

```bash
pip install cathode
```

## Quick start

Elements are composed with `box[child, ...]`. Stateful behavior lives in a `Widget` whose nested `Controller` declares reactive fields with `State`; assigning to a state field triggers a re-render.

```python
import asyncio
from cathode import Box, BaseController, State, Text, Widget, run

class Counter(Widget):
    class Controller(BaseController):
        count: int = State(0)

        def handle_input(self, ch: str) -> None:
            if ch == ' ':
                self.count += 1
            elif ch == 'q':
                self.exit()

        def contents(self):
            return [
                Text(text=f'Count: {self.count}'),
                Text(text='space: increment   q: quit'),
            ]

asyncio.run(run(Box()[Counter()]))
```

`run` draws into the normal terminal scrollback; pass `fullscreen=True` for a full-screen app in the terminal's alternate screen buffer.

## Learn more

The [`examples/`](examples) folder has more complete programs:

- [`chat.py`](examples/chat.py) — a streaming chat REPL with a `TextBox` prompt (append rendering).
- [`browser.py`](examples/browser.py) — a two-pane file browser with scrolling (alt-screen rendering).
- [`speedtest.py`](examples/speedtest.py) — animated progress bars using `Overlay` and `controller.exit()`.

## License

MIT — see [LICENSE](LICENSE).
