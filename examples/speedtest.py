"""Self-contained system speed test showing tqdm-style progress bars and a titled results box."""
from __future__ import annotations

import asyncio
import hashlib
import math
import time
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass

from cathode import Box, Component, Overlay, Text, Widget, render_root
from cathode.components import BaseController, State
from cathode.styles import Colors, Styles
from cathode.tree import ElementTree

ACCENT = '#5fafff'
GREEN = '#5fd75f'
BAR_WIDTH = 28
CARD_WIDTH = 60

KIB = 1024
MIB = 1024 * 1024


def hash_work(chunk: int) -> int:
    data = b'cathode' * 256
    for _ in range(chunk):
        hashlib.sha256(data).digest()
    return chunk

def hash_report(count: int, elapsed: float) -> tuple[str, float]:
    mbps = count * 256 * len(b'cathode') / MIB / elapsed
    return f'{mbps:,.0f} MB/s', mbps

def mem_work(chunk: int) -> int:
    buffer = bytearray(MIB)
    for _ in range(chunk):
        bytes(buffer)
    return chunk

def mem_report(count: int, elapsed: float) -> tuple[str, float]:
    gbps = count / KIB / elapsed
    return f'{gbps:,.1f} GB/s', gbps * 100

def math_work(chunk: int) -> int:
    total = 0.0
    for i in range(chunk):
        total += math.sqrt(i * 2.5 + 1.0)
    return chunk

def math_report(count: int, elapsed: float) -> tuple[str, float]:
    mops = count / 1e6 / elapsed
    return f'{mops:,.1f} Mops/s', mops


@dataclass
class Stage:
    """One measured benchmark phase: a unit of work, how long to run it, and how to report it."""

    key: str
    label: str
    budget: float
    chunk: int
    work: Callable[[int], int]
    report: Callable[[int, float], tuple[str, float]]

STAGES = [
    Stage('cpu', 'SHA-256', 1.2, 4000, hash_work, hash_report),
    Stage('memory', 'Memory', 1.2, 64, mem_work, mem_report),
    Stage('math', 'Float math', 1.2, 60000, math_work, math_report),
]


def bar(fraction: float) -> str:
    filled = round(fraction * BAR_WIDTH)
    return Colors.apply('█' * filled, ACCENT) + Styles.dim('░' * (BAR_WIDTH - filled))

def stage_row(label: str, fraction: float, value: str | None) -> str:
    right = Colors.apply(value, GREEN) if value else Styles.dim(f'{int(fraction * 100):3d}%')
    return f'{label:<11}' + bar(fraction) + '  ' + right

def titled_box(title: str, body: Component, color: str) -> Box:
    card = Box(width=CARD_WIDTH, border=['top', 'bottom', 'left', 'right'], border_color=color,
               padding={'left': 2, 'right': 2, 'top': 1, 'bottom': 1})[body]
    label = Text(text=Styles.bold(f' {title} '), text_color=color)
    return Box()[card, Overlay(top=0, left=2, height=1)[label]]


@dataclass
class SpeedTest(Widget):
    """Run each benchmark stage in turn, then present the measurements in a titled results box."""

    class Controller(BaseController):
        current: int = State(-1)
        fraction: float = State(0.0)
        results: dict[str, str] = State({})
        score: float = State(0.0)
        done: bool = State(False)
        _task: asyncio.Task | None = None

        def handle_mount(self, tree: ElementTree) -> None:
            super().handle_mount(tree)
            self._task = asyncio.create_task(self._run())

        async def _run(self) -> None:
            score = 0.0
            for index, stage in enumerate(STAGES):
                self.current, self.fraction = index, 0.0
                value, points = await self._run_stage(stage)
                self.results = {**self.results, stage.key: value}
                score += points
            self.score = score
            self.done = True
            self.exit()

        async def _run_stage(self, stage: Stage) -> tuple[str, float]:
            start = time.perf_counter()
            count = 0
            while (elapsed := time.perf_counter() - start) < stage.budget:
                count += stage.work(stage.chunk)
                self.fraction = min(1.0, elapsed / stage.budget)
                await asyncio.sleep(0)
            self.fraction = 1.0
            return stage.report(count, time.perf_counter() - start)

        def contents(self) -> list[Component | None]:
            rows = []
            for index, stage in enumerate(STAGES):
                value = self.results.get(stage.key)
                fraction = 1.0 if value else (self.fraction if index == self.current else 0.0)
                rows.append(Text(text=stage_row(stage.label, fraction, value)))

            if not self.done:
                header = Text(text=Styles.bold('Running speed test…'), text_color=ACCENT, margin={'bottom': 1})
                return [Box(margin={'top': 1, 'left': 1})[[header, *rows]]]

            summary = Text(text=f'{"Score":<11}' + Colors.apply(f'{self.score:,.0f}', ACCENT), margin={'top': 1})
            box = titled_box('speedtest results', Box()[[*rows, summary]], ACCENT)
            return [Box(margin={'top': 1, 'bottom': 1})[box]]


async def main() -> None:
    await render_root(SpeedTest())

if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        asyncio.run(main())
