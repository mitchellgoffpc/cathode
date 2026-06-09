"""Tests for cathode.styles ANSI helpers and text wrapping."""
import pytest

from cathode.styles import (
    Colors,
    Styles,
    Wrap,
    _ansi16m,
    _ansi256,
    ansi_len,
    ansi_slice,
    ansi_strip,
    iter_wrapped_lines,
    wrap_lines,
)


@pytest.mark.parametrize(("input_text", "expected"), [
    pytest.param("plain text", "plain text", id="plain text"),
    pytest.param(f"foo{Colors.RED}bar{Colors.END}baz", "foobarbaz", id="single color span"),
    pytest.param(f"{Styles.BOLD}[{Colors.BLUE}hello world{Colors.END}]{Styles.BOLD_END}", "[hello world]",
                 id="nested style and color spans"),
])
def test_ansi_strip(input_text: str, expected: str) -> None:
    assert ansi_strip(input_text) == expected


@pytest.mark.parametrize(("input_text", "expected"), [
    pytest.param("plain text", 10, id="plain text"),
    pytest.param(f"foo{Colors.RED}bar{Colors.END}baz", 9, id="single color span"),
    pytest.param(f"{Styles.BOLD}[{Colors.BLUE}hello world{Colors.END}]{Styles.BOLD_END}", 13,
                 id="nested style and color spans"),
])
def test_ansi_len(input_text: str, expected: int) -> None:
    assert ansi_len(input_text) == expected


@pytest.mark.parametrize(("text", "start", "end", "expected"), [
    pytest.param("hello world", 0, 5, "hello", id="basic slice"),
    pytest.param("hello world", 6, 11, "world", id="basic slice end"),
    pytest.param(f"{Colors.ansi('hello', Colors.RED)} world", 0, 5,
                 f"{Colors.RED}hello{Colors.END}", id="ansi16 colors"),
    pytest.param(f"{_ansi256(196)}hello{Colors.END} world", 0, 5,
                 f"{_ansi256(196)}hello{Colors.END}", id="ansi256 colors"),
    pytest.param(f"{_ansi16m(255, 0, 0)}hello{Colors.END} world", 0, 5,
                 f"{_ansi16m(255, 0, 0)}hello{Colors.END}", id="ansi16m colors"),
    pytest.param(f"{Colors.BG_RED}hello{Colors.BG_END} world", 0, 5,
                 f"{Colors.BG_RED}hello{Colors.BG_END}", id="background colors"),
    pytest.param(f"{Styles.BOLD}hello{Styles.BOLD_END} world", 0, 5,
                 f"{Styles.BOLD}hello{Styles.BOLD_END}", id="styles"),
    pytest.param(f"{Colors.RED}hello world{Colors.END}", 2, 8,
                 f"{Colors.RED}llo wo{Colors.END}", id="slice inside styled section"),
    pytest.param(f"{Colors.RED}hello{Colors.END} {Colors.BLUE}world{Colors.END}", 3, 8,
                 f"{Colors.RED}lo{Colors.END} {Colors.BLUE}wo{Colors.END}", id="slice across styled sections"),
    pytest.param(f"{Colors.RED}hello\nworld{Colors.END}", 3, 9,
                 f"{Colors.RED}lo\nwor{Colors.END}", id="multiline slice"),
    pytest.param(f"{Colors.RED}hello{Colors.END}", 0, 0, "", id="empty slice at start"),
    pytest.param(f"{Colors.RED}hello{Colors.END}", 5, 6, "", id="empty slice past end"),
    pytest.param(f"{Colors.END}a{Colors.RED}bcd{Colors.END}", 0, 3, f"a{Colors.RED}bc{Colors.END}",
                 id="slice starting with color reset"),
    pytest.param(f"{Styles.BOLD_END}a{Styles.BOLD}bcd{Styles.BOLD_END}", 0, 3, f"a{Styles.BOLD}bc{Styles.BOLD_END}",
                 id="slice starting with style reset"),
    pytest.param(f"{Colors.RED}{Colors.END}a{Colors.BLUE}{Colors.END}bc{Styles.BOLD}{Styles.BOLD_END}", 0, 3, "abc",
                 id="slice with empty ansi blocks"),
])
def test_ansi_slice(text: str, start: int, end: int, expected: str) -> None:
    result = ansi_slice(text, start, end)
    assert ansi_len(result) == min(ansi_len(text), end) - start
    assert result == expected


@pytest.mark.parametrize(("styled_text", "width"), [
    pytest.param("Hello World", 20, id="plain text"),
    pytest.param(f"{Colors.RED}A{Colors.END}", 1, id="single character"),
    pytest.param("line1\nline2", 5, id="multiple lines"),
    pytest.param(f"{Colors.RED}line1{Colors.END}\n{Colors.BLUE}line2{Colors.END}", 5, id="multiple styled lines"),
    pytest.param("line1\nline2\n", 5, id="trailing newline"),
])
def test_no_wrap(styled_text: str, width: int) -> None:
    assert wrap_lines(styled_text, width, wrap=Wrap.EXACT) == styled_text
    assert wrap_lines(styled_text, width, wrap=Wrap.WORDS) == styled_text


@pytest.mark.parametrize(("styled_text", "expected", "width"), [
    pytest.param(f"{Colors.RED}line\nline2{Colors.END}",
                 f"{Colors.RED}line{Colors.END}\n{Colors.RED}line2{Colors.END}", 5, id="one character short"),
    pytest.param(f"{Colors.RED}line1\nline2{Colors.END}",
                 f"{Colors.RED}line1{Colors.END}\n{Colors.RED}line2{Colors.END}", 5, id="exact fit"),
    pytest.param(f"{Colors.RED}line1\n\nline2{Colors.END}",
                 f"{Colors.RED}line1{Colors.END}\n\n{Colors.RED}line2{Colors.END}", 5, id="with empty line"),
])
def test_wrap_styled_lines(styled_text: str, expected: str, width: int) -> None:
    assert wrap_lines(styled_text, width, wrap=Wrap.EXACT) == expected
    assert wrap_lines(styled_text, width, wrap=Wrap.WORDS) == expected


def test_wrap_exact() -> None:
    styled_text = (f"{Colors.RED}This is a very {Styles.BOLD}long red text"
                   f"{Styles.BOLD_END} that should wrap{Colors.END}")
    expected_result = (
        f"{Colors.RED}This is a very {Styles.BOLD}long {Colors.END}{Styles.BOLD_END}\n"
        f"{Styles.BOLD}{Colors.RED}red text{Styles.BOLD_END} that should{Colors.END}\n"
        f"{Colors.RED} wrap{Colors.END}")
    assert wrap_lines(styled_text, 20, wrap=Wrap.EXACT) == expected_result

    styled_text = f"{Colors.RED}This is:\na very long red text that should wrap.{Colors.END}"
    expected_result = (
        f"{Colors.RED}This is:{Colors.END}\n"
        f"{Colors.RED}a very long red text{Colors.END}\n"
        f"{Colors.RED} that should wrap.{Colors.END}")
    assert wrap_lines(styled_text, 20, wrap=Wrap.EXACT) == expected_result


@pytest.mark.parametrize(("input_text", "expected", "width"), [
    pytest.param("This is a very long line", "This is a\nvery long\nline", 10, id="simple wrap"),
    pytest.param("supercalifragilistic", "supercal\nifragili\nstic", 8, id="long word break"),
    pytest.param("hello world", "hello\nworld", 5, id="word exact length"),
    pytest.param("test    space\n  a", "test \nspace\n  a", 5, id="leading whitespace"),
])
def test_wrap_words(input_text: str, expected: str, width: int) -> None:
    assert wrap_lines(input_text, width, wrap=Wrap.WORDS) == expected


@pytest.mark.parametrize(("input_text", "expected", "width"), [
    pytest.param("hello", "hello", 10, id="ellipsis fits"),
    pytest.param("hello world", "hell…", 5, id="ellipsis truncate"),
    pytest.param("hello world\nfoo", "hell…\nfoo", 5, id="ellipsis preserves newlines"),
    pytest.param("foo\nlong line here", "foo\nlong…", 5, id="ellipsis truncates later line"),
    pytest.param("abcdef", "…", 1, id="ellipsis width 1"),
])
def test_wrap_ellipsis(input_text: str, expected: str, width: int) -> None:
    assert wrap_lines(input_text, width, wrap=Wrap.ELLIPSIS) == expected


@pytest.mark.parametrize(("text", "width", "wrap", "expected"), [
    pytest.param("hello world foo", 10, Wrap.WORDS, [(0, 5), (6, 15)], id="words soft wrap at space"),
    pytest.param("supercalifragilistic", 8, Wrap.WORDS, [(0, 8), (8, 16), (16, 20)], id="words long word break"),
    pytest.param("a\nb\nc", 5, Wrap.EXACT, [(0, 1), (2, 3), (4, 5)], id="exact hard newlines"),
    pytest.param("a   \nb", 3, Wrap.WORDS, [(0, 3), (5, 6)], id="words skip leading whitespace on continuation"),
    pytest.param("ab\n", 5, Wrap.EXACT, [(0, 2), (3, 3)], id="trailing newline emits empty line"),
])
def test_iter_wrapped_lines_source_indices(text: str, width: int, wrap: Wrap, expected: list[tuple[int, int]]) -> None:
    bounds = [(s.source_start, s.source_end) for s in iter_wrapped_lines(text, width, wrap)]
    assert bounds == expected


@pytest.mark.parametrize(("input_text", "expected", "width"), [
    pytest.param("supercalifragilistic", "superca\nlifragi\nlistic", 8, id="long word wraps at width-1"),
    pytest.param("this is a test", "this \nis a \ntest", 7, id="exact width lines wrap"),
    pytest.param("this is a test", "this is \na test", 8, id="keeps trailing space on wrap boundary"),
    pytest.param("x    " + Styles.inverse(' ') + " t", "x " + Styles.inverse(' ') + "\nt", 3,
                 id="cursor past wrap point is clamped"),
    pytest.param('\n' + Styles.inverse(' '), '\n' + Styles.inverse(' '), 10, id="cursor appears on second line"),
])
def test_wrap_words_with_cursor(input_text: str, expected: str, width: int) -> None:
    wrapped = wrap_lines(input_text, width, wrap=Wrap.WORDS_WITH_CURSOR)
    assert wrapped == expected
