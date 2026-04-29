"""Tests for cathode.termcolor color spec parsing."""
import pytest

from cathode.termcolor import _parse_color_spec


@pytest.mark.parametrize(("spec", "expected"), [
    pytest.param("rgb:ffff/0000/8080", (255, 0, 128), id="rgb 4-digit"),
    pytest.param("rgb:ff/00/80", (255, 0, 128), id="rgb 2-digit"),
    pytest.param("  rgb:ffff/0000/8080  ", (255, 0, 128), id="rgb with surrounding whitespace"),
    pytest.param("rgb:ff/00", None, id="rgb with too few components"),
    pytest.param("#ff0080", (255, 0, 128), id="6-char hex"),
    pytest.param("f08", (255, 0, 136), id="3-char hex expanded"),
    pytest.param("0", (0, 0, 0), id="xterm index 0"),
    pytest.param("15", (255, 255, 255), id="xterm index 15"),
    pytest.param("16", None, id="xterm index out of range"),
    pytest.param("garbage", None, id="unparseable"),
])
def test_parse_color_spec(spec: str, expected: tuple[int, int, int] | None) -> None:
    assert _parse_color_spec(spec) == expected
