"""ELIZA-style chat REPL demonstrating cathode's main-screen append rendering."""
from __future__ import annotations

import asyncio
import random
import re
from contextlib import suppress
from dataclasses import dataclass

from cathode import Box, Colors, Component, Text, TextBox, Widget, render_root
from cathode.components import BaseController, State
from cathode.styles import Color

USER_COLOR = '#5fafff'
BOT_COLOR = '#ff87d7'

ELIZA_PATTERNS: list[tuple[str, list[str]]] = [
    (r"i need (.*)", ["Why do you need {0}?", "Would it really help you to get {0}?"]),
    (r"why don'?t you (.*)", ["Do you really think I don't {0}?", "Perhaps eventually I will {0}."]),
    (r"i can'?t (.*)", ["How do you know you can't {0}?", "Have you really tried?"]),
    (r"i am (.*)", ["How long have you been {0}?", "Why do you say you are {0}?"]),
    (r"i'?m (.*)", ["How does being {0} make you feel?", "Do you enjoy being {0}?"]),
    (r"because (.*)", ["Is that the real reason?", "What other reasons come to mind?"]),
    (r"(.*) sorry (.*)", ["Please don't apologize. Apologies are not necessary."]),
    (r"hello(.*)", ["Hello. How are you feeling today?", "Hi there. What's on your mind?"]),
    (r"i think (.*)", ["Do you doubt {0}?", "Do you really think so?"]),
    (r"(.*) friend(.*)", ["Tell me more about your friends.", "Why do you bring up the topic of friends?"]),
    (r"yes", ["You seem quite sure.", "OK, but can you elaborate a bit?"]),
    (r"no", ["Why not?", "Are you sure?"]),
    (r"(.*) computer(.*)", ["Do computers worry you?", "Why do you mention computers?"]),
    (r"(.*)\?", ["Why do you ask?", "What do you think?", "What would it mean if you got an answer?"]),
    (r"(.*)", ["Please tell me more.", "Let's change focus a bit. Tell me about your family.",
               "How does that make you feel?", "I see. Go on.", "Can you elaborate on that?"]),
]

REFLECTIONS = {
    "i": "you", "me": "you", "my": "your", "am": "are",
    "you": "I", "your": "my", "yours": "mine", "are": "am",
}

def reflect(fragment: str) -> str:
    return ' '.join(REFLECTIONS.get(w.lower(), w) for w in fragment.split())

def eliza_reply(text: str) -> str:
    text = text.strip().rstrip('.!')
    for pattern, responses in ELIZA_PATTERNS:
        match = re.match(pattern, text, flags=re.IGNORECASE)
        if match:
            template = random.choice(responses)
            return template.format(*[reflect(g) for g in match.groups()])
    return "Tell me more."


def bubble(sender: str, text: str, color: Color) -> Component:
    label = Text(text=Colors.apply(sender, color=color), padding={'left': 1, 'right': 1})
    body = Text(text=text, padding={'left': 1, 'right': 1})
    return Box(border=['top', 'bottom', 'left', 'right'], border_color=color, margin={'top': 1})[label, body]


@dataclass
class Chat(Widget):
    """Chat transcript with a streaming ELIZA responder and a TextBox prompt."""

    class Controller(BaseController):
        messages: list[tuple[str, str]] = State([])
        pending: str = State('')
        _task: asyncio.Task | None = None

        def on_submit(self, text: str) -> bool:
            if not text.strip() or self._task and not self._task.done():
                return False
            self.messages = [*self.messages, ('you', text)]
            self._task = asyncio.create_task(self._stream_reply(text))
            return True

        async def _stream_reply(self, user_text: str) -> None:
            response = eliza_reply(user_text)
            self.pending = ''
            for ch in response:
                self.pending = self.pending + ch
                await asyncio.sleep(0.025)
            self.messages = [*self.messages, ('eliza', self.pending)]
            self.pending = ''

        def contents(self) -> list[Component | None]:
            bubbles: list[Component | None] = [
                bubble(sender, text, USER_COLOR if sender == 'you' else BOT_COLOR)
                for sender, text in self.messages
            ]
            if self.pending:
                bubbles.append(bubble('eliza', self.pending, BOT_COLOR))
            prompt = TextBox(placeholder='Talk to ELIZA (Ctrl+C to quit)...', handle_submit=self.on_submit)
            framed = Box(
                border=['top', 'bottom', 'left', 'right'], border_color=USER_COLOR,
                padding={'left': 1, 'right': 1}, margin={'top': 1},
            )[prompt]
            return [Box()[bubbles], framed]


async def main() -> None:
    intro = Text(text=Colors.apply('ELIZA is listening.', color=BOT_COLOR))
    await render_root(Box()[intro, Chat()])

if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        asyncio.run(main())
