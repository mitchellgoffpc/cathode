"""Styling primitives: colors, borders, text wrapping, and ANSI-aware string utilities."""
import os
import re
import unicodedata
from collections import defaultdict, deque
from collections.abc import Iterator
from enum import Enum
from typing import NamedTuple

ANSI_BACKGROUND_OFFSET = 10
ANSI_256_SUPPORT = '256color' in os.getenv("TERM", '')
ANSI_16M_SUPPORT = 'truecolor' in os.getenv("COLORTERM", '') or '24bit' in os.getenv("COLORTERM", '')
ANSI_RE = re.compile('\u001B\\[[0-9;]+m')

Color = str | tuple[int, int, int]

class Axis(Enum):
    """Layout axis along which a container arranges its children."""

    VERTICAL = 'vertical'
    HORIZONTAL = 'horizontal'

class Wrap(Enum):
    """Strategy used to wrap text that exceeds the available width."""

    EXACT = 'exact'
    WORDS = 'words'
    WORDS_WITH_CURSOR = 'words_with_cursor'

class WrappedLine(NamedTuple):
    """A single visual line produced by `iter_wrapped_lines`."""

    text: str
    width: int
    source_start: int
    source_end: int
    hard_break: bool

class BorderStyle(NamedTuple):
    """Glyphs used to draw the eight segments of a box border."""

    top_left: str
    top: str
    top_right: str
    right: str
    bottom_right: str
    bottom: str
    bottom_left: str
    left: str

class Borders:
    """Predefined `BorderStyle` presets for common border appearances."""

    SINGLE = BorderStyle("┌", "─", "┐", "│", "┘", "─", "└", "│")
    DOUBLE = BorderStyle("╔", "═", "╗", "║", "╝", "═", "╚", "║")
    ROUND = BorderStyle("╭", "─", "╮", "│", "╯", "─", "╰", "│")
    BOLD = BorderStyle("┏", "━", "┓", "┃", "┛", "━", "┗", "┃")
    SINGLE_DOUBLE = BorderStyle("╓", "─", "╖", "║", "╜", "─", "╙", "║")
    DOUBLE_SINGLE = BorderStyle("╒", "═", "╕", "│", "╛", "═", "╘", "│")
    CLASSIC = BorderStyle("+", "-", "+", "|", "+", "-", "+", "|")

class Styles:
    """ANSI text-style escape codes and helpers for applying them to strings."""

    RESET = "\u001B[0m"
    BOLD = "\u001B[1m"
    DIM = "\u001B[2m"
    ITALIC = "\u001B[3m"
    UNDERLINE = "\u001B[4m"
    OVERLINE = "\u001B[53m"
    INVERSE = "\u001B[7m"
    HIDDEN = "\u001B[8m"
    STRIKETHROUGH = "\u001B[9m"

    BOLD_END = "\u001B[22m"
    DIM_END = "\u001B[22m"
    ITALIC_END = "\u001B[23m"
    UNDERLINE_END = "\u001B[24m"
    OVERLINE_END = "\u001B[55m"
    INVERSE_END = "\u001B[27m"
    HIDDEN_END = "\u001B[28m"
    STRIKETHROUGH_END = "\u001B[29m"

    @staticmethod
    def bold(text: str) -> str:
        """Wrap `text` in ANSI bold escape codes."""
        return _apply_style(text, start=Styles.BOLD, end=Styles.BOLD_END)
    @staticmethod
    def dim(text: str) -> str:
        """Wrap `text` in ANSI dim escape codes."""
        return _apply_style(text, start=Styles.DIM, end=Styles.DIM_END)
    @staticmethod
    def italic(text: str) -> str:
        """Wrap `text` in ANSI italic escape codes."""
        return _apply_style(text, start=Styles.ITALIC, end=Styles.ITALIC_END)
    @staticmethod
    def underline(text: str) -> str:
        """Wrap `text` in ANSI underline escape codes."""
        return _apply_style(text, start=Styles.UNDERLINE, end=Styles.UNDERLINE_END)
    @staticmethod
    def overline(text: str) -> str:
        """Wrap `text` in ANSI overline escape codes."""
        return _apply_style(text, start=Styles.OVERLINE, end=Styles.OVERLINE_END)
    @staticmethod
    def inverse(text: str) -> str:
        """Wrap `text` in ANSI inverse-video escape codes."""
        return _apply_style(text, start=Styles.INVERSE, end=Styles.INVERSE_END)
    @staticmethod
    def hidden(text: str) -> str:
        """Wrap `text` in ANSI hidden escape codes."""
        return _apply_style(text, start=Styles.HIDDEN, end=Styles.HIDDEN_END)
    @staticmethod
    def strikethrough(text: str) -> str:
        """Wrap `text` in ANSI strikethrough escape codes."""
        return _apply_style(text, start=Styles.STRIKETHROUGH, end=Styles.STRIKETHROUGH_END)

class Colors:
    """ANSI color escape codes for the standard 16 foreground and background colors."""

    BLACK = "\u001B[30m"
    RED = "\u001B[31m"
    GREEN = "\u001B[32m"
    YELLOW = "\u001B[33m"
    BLUE = "\u001B[34m"
    MAGENTA = "\u001B[35m"
    CYAN = "\u001B[36m"
    WHITE = "\u001B[37m"
    BLACK_BRIGHT = "\u001B[90m"
    RED_BRIGHT = "\u001B[91m"
    GREEN_BRIGHT = "\u001B[92m"
    YELLOW_BRIGHT = "\u001B[93m"
    BLUE_BRIGHT = "\u001B[94m"
    MAGENTA_BRIGHT = "\u001B[95m"
    CYAN_BRIGHT = "\u001B[96m"
    WHITE_BRIGHT = "\u001B[97m"
    END = "\u001B[39m"

    BG_BLACK = "\u001B[40m"
    BG_RED = "\u001B[41m"
    BG_GREEN = "\u001B[42m"
    BG_YELLOW = "\u001B[43m"
    BG_BLUE = "\u001B[44m"
    BG_MAGENTA = "\u001B[45m"
    BG_CYAN = "\u001B[46m"
    BG_WHITE = "\u001B[47m"
    BG_BLACK_BRIGHT = "\u001B[100m"
    BG_RED_BRIGHT = "\u001B[101m"
    BG_GREEN_BRIGHT = "\u001B[102m"
    BG_YELLOW_BRIGHT = "\u001B[103m"
    BG_BLUE_BRIGHT = "\u001B[104m"
    BG_MAGENTA_BRIGHT = "\u001B[105m"
    BG_CYAN_BRIGHT = "\u001B[106m"
    BG_WHITE_BRIGHT = "\u001B[107m"
    BG_END = "\u001B[49m"

    @staticmethod
    def HEX(code: str) -> str:
        """Return the foreground ANSI escape for the hex color `code`."""
        return _hex_to_best_ansi(code)
    @staticmethod
    def RGB(rgb: tuple[int, int, int]) -> str:
        """Return the foreground ANSI escape for the given RGB triple."""
        return _rgb_to_best_ansi(*rgb)
    @staticmethod
    def BG_HEX(code: str) -> str:
        """Return the background ANSI escape for the hex color `code`."""
        return _hex_to_best_ansi(code, offset=ANSI_BACKGROUND_OFFSET)
    @staticmethod
    def BG_RGB(rgb: tuple[int, int, int]) -> str:
        """Return the background ANSI escape for the given RGB triple."""
        return _rgb_to_best_ansi(*rgb, offset=ANSI_BACKGROUND_OFFSET)

    @staticmethod
    def ansi(text: str, code: str) -> str:
        """Wrap `text` in the given foreground ANSI `code` and a reset."""
        return _apply_style(text, start=code, end=Colors.END)
    @staticmethod
    def hex(text: str, code: str) -> str:
        """Color `text` with the foreground hex color `code`."""
        return _apply_style(text, start=_hex_to_best_ansi(code), end=Colors.END)
    @staticmethod
    def rgb(text: str, rgb: tuple[int, int, int]) -> str:
        """Color `text` with the foreground RGB triple."""
        return _apply_style(text, start=_rgb_to_best_ansi(*rgb), end=Colors.END)

    @staticmethod
    def bg_ansi(text: str, code: str) -> str:
        """Wrap `text` in the given background ANSI `code` and a reset, if `code` is non-empty."""
        return _apply_style(text, start=code, end=Colors.BG_END) if code else text
    @staticmethod
    def bg_hex(text: str, code: str) -> str:
        """Color the background of `text` with the hex color `code`."""
        return _apply_style(text, start=_hex_to_best_ansi(code, offset=ANSI_BACKGROUND_OFFSET), end=Colors.BG_END)
    @staticmethod
    def bg_rgb(text: str, rgb: tuple[int, int, int]) -> str:
        """Color the background of `text` with the RGB triple."""
        return _apply_style(text, start=_rgb_to_best_ansi(*rgb, offset=ANSI_BACKGROUND_OFFSET), end=Colors.BG_END)

    @staticmethod
    def apply(text: str, color: Color | None) -> str:
        """Apply `color` to the foreground of `text`, accepting either a hex string or RGB triple."""
        return _apply_style(text, start=color_to_ansi(color, background=False), end=Colors.END)
    @staticmethod
    def apply_bg(text: str, color: Color | None) -> str:
        """Apply `color` to the background of `text`, accepting either a hex string or RGB triple."""
        return _apply_style(text, start=color_to_ansi(color, background=True), end=Colors.BG_END)

    @staticmethod
    def blend(a: tuple[int, int, int], b: tuple[int, int, int], alpha: float) -> tuple[int, int, int]:
        """Linearly interpolate between RGB colors `a` and `b` by `alpha` (1.0 = `a`, 0.0 = `b`)."""
        red = int(a[0] * alpha + b[0] * (1.0 - alpha))
        green = int(a[1] * alpha + b[1] * (1.0 - alpha))
        blue = int(a[2] * alpha + b[2] * (1.0 - alpha))
        return red, green, blue


# ANSI color helpers

LEVELS = [0, 95, 135, 175, 215, 255]
XTERM_COLORS: dict[int, tuple[int, int, int]] = (
    {16 + 36 * r + 6 * g + b: (LEVELS[r], LEVELS[g], LEVELS[b]) for r in range(6) for g in range(6) for b in range(6)} |
    {232 + i: (8 + 10 * i, 8 + 10 * i, 8 + 10 * i) for i in range(24)})

def _srgb_to_linear(value: int) -> float:
    c = value / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def _rgb_to_xyz(r: int, g: int, b: int) -> tuple[float, float, float]:
    x, y, z = _srgb_to_linear(r), _srgb_to_linear(g), _srgb_to_linear(b)
    return (
        x * 0.4124 + y * 0.3576 + z * 0.1805,
        x * 0.2126 + y * 0.7152 + z * 0.0722,
        x * 0.0193 + y * 0.1192 + z * 0.9505)

def _xyz_to_lab(x: float, y: float, z: float) -> tuple[float, float, float]:
    xr, yr, zr = x / 0.95047, y / 1.00000, z / 1.08883
    def f(t: float) -> float:
        return t ** (1.0 / 3.0) if t > 0.008856 else 7.787 * t + 16.0 / 116.0
    fx, fy, fz = f(xr), f(yr), f(zr)
    return 116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz)

def _perceptual_distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    x1, y1, z1 = _rgb_to_xyz(*a)
    x2, y2, z2 = _rgb_to_xyz(*b)
    l1, a1, b1 = _xyz_to_lab(x1, y1, z1)
    l2, a2, b2 = _xyz_to_lab(x2, y2, z2)
    dl, da, db = l1 - l2, a1 - a2, b1 - b2
    return (dl * dl + da * da + db * db) ** 0.5

def _rgb_to_ansi256(red: int, green: int, blue: int) -> int:
    return min(XTERM_COLORS, key=lambda i: _perceptual_distance(XTERM_COLORS[i], (red, green, blue)))

def _ansi256_to_ansi(code: int) -> int:
    if code < 8:
        return 30 + code
    if code < 16:
        return 90 + (code - 8)

    if code >= 232:
        red = (((code - 232) * 10) + 8) / 255
        green = red
        blue = red
    else:
        code -= 16
        remainder = code % 36
        red = (code // 36) / 5
        green = (remainder // 6) / 5
        blue = (remainder % 6) / 5

    value = max(red, green, blue) * 2
    if value == 0:
        return 30

    result = 30 + ((round(blue) << 2) | (round(green) << 1) | round(red))
    if value == 2:
        result += 60

    return result

def _rgb_to_best_ansi(red: int, green: int, blue: int, *, offset: int = 0) -> str:
    if ANSI_16M_SUPPORT:
        return _ansi16m(red, green, blue, offset=offset)
    elif ANSI_256_SUPPORT:
        code = _rgb_to_ansi256(red, green, blue)
        return _ansi256(code, offset=offset)
    else:
        code = _ansi256_to_ansi(_rgb_to_ansi256(red, green, blue))
        return _ansi16(code, offset=offset)

def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    matches = re.search(r'[a-f\d]{6}|[a-f\d]{3}', str(hex_str), re.IGNORECASE)
    if not matches:
        return (0, 0, 0)

    color_string = matches.group(0)
    if len(color_string) == 3:
        color_string = ''.join([c + c for c in color_string])

    integer = int(color_string, 16)
    return (integer >> 16) & 0xFF, (integer >> 8) & 0xFF, integer & 0xFF

def _hex_to_best_ansi(hex_str: str, *, offset: int = 0) -> str:
    return _rgb_to_best_ansi(*_hex_to_rgb(hex_str), offset=offset)

def color_to_ansi(color: Color | None, *, background: bool) -> str:
    """Return the foreground or background ANSI escape for `color`, or empty string for `None`."""
    offset = ANSI_BACKGROUND_OFFSET if background else 0
    match color:
        case None: return ''
        case (int(r), int(g), int(b)): return _rgb_to_best_ansi(r, g, b, offset=offset)
        case str() as hex_color: return _hex_to_best_ansi(hex_color, offset=offset)
        case _: raise ValueError(f"Invalid color value: {color}")


# ANSI escape helpers

def _apply_style(text: str, start: str, end: str) -> str:
    return f"{start}{text}{end}" if start else text

def _ansi16(code: int, *, offset: int = 0) -> str:
    return f"\u001B[{code + offset}m"

def _ansi256(code: int, *, offset: int = 0) -> str:
    return f"\u001B[{38 + offset};5;{code}m"

def _ansi16m(red: int, green: int, blue: int, *, offset: int = 0) -> str:
    return f"\u001B[{38 + offset};2;{red};{green};{blue}m"

def ansi_len(text: str) -> int:
    """Return the visual width of `text` in columns, ignoring ANSI escapes and counting wide chars as 2."""
    return sum(2 if unicodedata.east_asian_width(c) in 'FW' else 1 for c in ansi_strip(text))

def ansi_strip(text: str) -> str:
    """Return `text` with all ANSI SGR escape sequences removed."""
    return re.sub(r'\u001B\[[0-9;]+m', '', text)

def ansi_slice(string: str, start: int, end: int) -> str:
    """Return the substring of `string` between visual columns `start` and `end`, preserving styling."""
    style_starts_to_stops = {}
    style_stops_to_starts = defaultdict(list)
    for attr_name, attr_value in Styles.__dict__.items():
        if attr_name.endswith('_END'):
            start_code = Styles.__dict__[attr_name.removesuffix('_END')]
            style_stops_to_starts[attr_value].append(start_code)
        else:
            style_starts_to_stops[attr_value] = Styles.__dict__.get(attr_name + '_END', Styles.RESET)

    ansi_pattern = re.compile(r'\u001B\[([0-9;]+)m')
    chunks = []
    last_pos = 0

    for match in ansi_pattern.finditer(string):
        if match.start() > last_pos:
            chunks.append(string[last_pos:match.start()])
        chunks.append(match.group())
        last_pos = match.end()
    if last_pos < len(string):
        chunks.append(string[last_pos:])

    result = []
    current_pos = 0
    active_styles: dict[str, bool] = {}
    active_color = active_bgcolor = ('', False)

    for chunk in chunks:
        if match_ := ansi_pattern.match(chunk):
            codes = deque(match_.group(1).split(';'))
            while codes:
                code = int(codes.popleft())
                ansi_code = f'\u001B[{code}m'
                if code in (38, 48) and codes:
                    if codes[0] == '5' and len(codes) >= 2:
                        _, color_code = codes.popleft(), codes.popleft()
                        ansi_code = f'\u001B[{code};5;{color_code}m'
                    elif codes[0] == '2' and len(codes) >= 4:
                        _, r, g, b = codes.popleft(), codes.popleft(), codes.popleft(), codes.popleft()
                        ansi_code = f'\u001B[{code};2;{r};{g};{b}m'

                if code == 0:
                    if any(active_styles.values()) or active_color[1] or active_bgcolor[1]:
                        result.append(Styles.RESET)
                    active_styles.clear()
                    active_color = active_bgcolor = ('', False)
                elif code in range(30, 39) or code in range(90, 98):
                    active_color = (ansi_code, False)
                elif code in range(40, 49) or code in range(100, 108):
                    active_bgcolor = (ansi_code, False)
                elif code == 39:
                    if active_color[1]:
                        result.append(Colors.END)
                    active_color = ('', False)
                elif code == 49:
                    if active_bgcolor[1]:
                        result.append(Colors.BG_END)
                    active_bgcolor = ('', False)
                elif ansi_code in style_starts_to_stops:
                    active_styles[ansi_code] = False
                elif ansi_code in style_stops_to_starts:
                    if any(active_styles.get(style, False) for style in style_stops_to_starts[ansi_code]):
                        result.append(ansi_code)
                    for style in style_stops_to_starts[ansi_code]:
                        active_styles.pop(style, None)

        else:
            chunk_end = current_pos + len(chunk)
            if chunk_end <= start:
                current_pos = chunk_end
                continue
            if current_pos >= end:
                break

            slice_start = max(0, start - current_pos)
            slice_end = min(len(chunk), end - current_pos)
            if slice_start < slice_end:
                for style_code, has_style_content in active_styles.items():
                    if not has_style_content:
                        result.append(style_code)
                        active_styles[style_code] = True
                if active_color[0] and not active_color[1]:
                    result.append(active_color[0])
                    active_color = (active_color[0], True)
                if active_bgcolor[0] and not active_bgcolor[1]:
                    result.append(active_bgcolor[0])
                    active_bgcolor = (active_bgcolor[0], True)
                result.append(chunk[slice_start:slice_end])
            if chunk_end >= end:
                break
            current_pos = chunk_end

    reset = ''
    if active_color[0] and active_color[1]:
        reset += Colors.END
    if active_bgcolor[0] and active_bgcolor[1]:
        reset += Colors.BG_END
    for style, used in active_styles.items():
        if used:
            reset += style_starts_to_stops[style]
    return ''.join(result) + reset

def _advance_source(content: str, src: int, visual_cols: int) -> int:
    cols = 0
    while src < len(content) and cols < visual_cols:
        if m := ANSI_RE.match(content, src):
            src = m.end()
            continue
        cols += 2 if unicodedata.east_asian_width(content[src]) in 'FW' else 1
        src += 1
    return src

def iter_wrapped_lines(content: str, max_width: int, wrap: Wrap = Wrap.EXACT) -> Iterator[WrappedLine]:
    """Wrap `content` to `max_width` columns, yielding one `WrappedLine` per visual line."""
    if wrap is Wrap.WORDS_WITH_CURSOR:
        max_width -= 1
    if max_width <= 0:
        return
    segments: list[WrappedLine] = []
    pos = src = 0
    wrapped = False
    acc_text, acc_width, acc_start = '', 0, -1

    while line := ansi_slice(content, pos, pos + max_width + 1):
        plaintext = ansi_strip(line)
        if leading_newlines := len(plaintext) - len(plaintext.lstrip('\n')):
            for i in range(leading_newlines):
                if i == 0 and wrapped:
                    wrapped = False
                else:
                    start = acc_start if acc_start >= 0 else src
                    segments.append(WrappedLine(acc_text, acc_width, start, src, hard_break=True))
                    acc_text, acc_width, acc_start = '', 0, -1
                src += 1
                pos += 1
            continue

        leading_whitespace = len(plaintext) - len(plaintext.lstrip(' \t'))
        if wrap in (Wrap.WORDS, Wrap.WORDS_WITH_CURSOR) and leading_whitespace:
            ws_advance = _advance_source(content, src, leading_whitespace) - src
            if wrapped:
                # Handles a cursor off the right side of the textbox boundary, capping it at the edge
                cursor_pos_in_line = len(line) - len(line.lstrip(' \t'))
                if wrap is Wrap.WORDS_WITH_CURSOR and cursor_pos_in_line < leading_whitespace:
                    last = segments[-1]
                    stub = ansi_slice(line, cursor_pos_in_line, cursor_pos_in_line + 1)
                    new_text = ansi_slice(last.text, 0, last.width - 1) + stub
                    segments[-1] = WrappedLine(
                        new_text, last.width, last.source_start, last.source_end + ws_advance, last.hard_break)
            else:
                if acc_start < 0:
                    acc_start = src
                acc_text += ansi_slice(line, 0, leading_whitespace)
                acc_width += leading_whitespace
            pos += leading_whitespace
            src += ws_advance
            continue

        if (newline_pos := plaintext.find('\n')) >= 0:
            text = ansi_slice(content, pos, pos + newline_pos)
            new_src = _advance_source(content, src, newline_pos)
            start = acc_start if acc_start >= 0 else src
            segments.append(WrappedLine(acc_text + text, acc_width + newline_pos, start, new_src, hard_break=True))
            acc_text, acc_width, acc_start = '', 0, -1
            pos += newline_pos + 1
            src = new_src + 1
            wrapped = False
        elif wrap is Wrap.EXACT or ' ' not in plaintext or len(plaintext) <= max_width:
            text = ansi_slice(content, pos, pos + max_width)
            new_src = _advance_source(content, src, max_width)
            start = acc_start if acc_start >= 0 else src
            segments.append(WrappedLine(acc_text + text, acc_width + ansi_len(text), start, new_src, hard_break=False))
            acc_text, acc_width, acc_start = '', 0, -1
            pos += max_width
            src = new_src
            wrapped = True
        else:
            break_pos = max_width if plaintext[-1] == ' ' else plaintext.rfind(' ')
            slice_end = break_pos + (1 if wrap is Wrap.WORDS_WITH_CURSOR else 0)
            text = ansi_slice(content, pos, pos + slice_end)
            seg_end = _advance_source(content, src, slice_end)
            new_src = _advance_source(content, src, break_pos + 1)
            start = acc_start if acc_start >= 0 else src
            segments.append(WrappedLine(acc_text + text, acc_width + ansi_len(text), start, seg_end, hard_break=False))
            acc_text, acc_width, acc_start = '', 0, -1
            pos += break_pos + 1
            src = new_src
            wrapped = True

    if acc_start >= 0:
        segments.append(WrappedLine(acc_text, acc_width, acc_start, src, hard_break=False))
    elif segments and segments[-1].hard_break:
        segments.append(WrappedLine('', 0, src, src, hard_break=False))
    yield from segments

def wrap_lines(content: str, max_width: int, wrap: Wrap = Wrap.EXACT) -> str:
    """Wrap `content` to `max_width` columns using the strategy specified by `wrap`."""
    return '\n'.join(seg.text for seg in iter_wrapped_lines(content, max_width, wrap))
