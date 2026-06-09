"""Named constants for the input sequences delivered to widget `handle_input` hooks."""

class Keys:
    """Input sequences for common keys, as delivered to `handle_input`."""

    UP = '\x1b[A'
    DOWN = '\x1b[B'
    RIGHT = '\x1b[C'
    LEFT = '\x1b[D'
    HOME = '\x1b[H'
    END = '\x1b[F'
    INSERT = '\x1b[2~'
    DELETE = '\x1b[3~'
    PAGE_UP = '\x1b[5~'
    PAGE_DOWN = '\x1b[6~'

    ENTER = '\r'
    TAB = '\t'
    SHIFT_TAB = '\x1b[Z'
    BACKSPACE = '\x7f'
    ESCAPE = '\x1b'
    SPACE = ' '

    F1 = '\x1bOP'
    F2 = '\x1bOQ'
    F3 = '\x1bOR'
    F4 = '\x1bOS'
    F5 = '\x1b[15~'
    F6 = '\x1b[17~'
    F7 = '\x1b[18~'
    F8 = '\x1b[19~'
    F9 = '\x1b[20~'
    F10 = '\x1b[21~'
    F11 = '\x1b[23~'
    F12 = '\x1b[24~'

    @staticmethod
    def ctrl(ch: str) -> str:
        """Return the control character sent for Ctrl+`ch` (for example `Keys.ctrl('c')`)."""
        return chr(ord(ch.upper()) % 32)

    @staticmethod
    def alt(ch: str) -> str:
        """Return the escape sequence sent for Alt+`ch` (for example `Keys.alt('b')`)."""
        return '\x1b' + ch
