"""The trimming the panel API applies to every request string before it verifies the checksum.

Laravel 13 global ``TrimStrings`` middleware (``Illuminate\\Support\\Str::trim()``) runs on every
``/api/v1/pbl/*`` request. A signed string with any of these characters at either end would be hashed by the
API without them and answered 401 "Unauthorized request", so the SDK sends and signs the trimmed value.
Characters inside the string are kept. Python's ``str.strip()`` is not the same set (it also strips
U+001C-U+001F and keeps U+0000, U+00AD, U+200B, U+FEFF...).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from dpay._internal.checksum import ChecksumCalculator
from dpay.exceptions import DPayValueError

# Code points removed from both ends: ``\s`` of PCRE2 in UTF/UCP mode (tab, LF, VT, FF, CR, space, NEL, the Z
# category), NUL and Laravel's ``Str::INVISIBLE_CHARACTERS`` - 65 code points.
CODE_POINTS: frozenset[int] = frozenset(
    (
        0x0000, 0x0009, 0x000A, 0x000B, 0x000C, 0x000D, 0x0020, 0x0085, 0x00A0, 0x00AD, 0x034F, 0x061C,
        0x115F, 0x1160, 0x1680, 0x17B4, 0x17B5, 0x180E, 0x2000, 0x2001, 0x2002, 0x2003, 0x2004, 0x2005,
        0x2006, 0x2007, 0x2008, 0x2009, 0x200A, 0x200B, 0x200C, 0x200D, 0x200E, 0x200F, 0x2028, 0x2029,
        0x202F, 0x205F, 0x2060, 0x2061, 0x2062, 0x2063, 0x2064, 0x2065, 0x206A, 0x206B, 0x206C, 0x206D,
        0x206E, 0x206F, 0x2800, 0x3000, 0x3164, 0xFEFF, 0xFFA0, 0x1D159, 0x1D173, 0x1D174, 0x1D175, 0x1D176,
        0x1D177, 0x1D178, 0x1D179, 0x1D17A, 0xE0020,
    )
)  # fmt: skip

_CHARACTERS = "".join(chr(code_point) for code_point in sorted(CODE_POINTS))


def server_trim(value: str) -> str:
    """``value`` without the trimmed code points at either end (a Python ``str`` is already code points)."""
    return value.strip(_CHARACTERS)


def trim_strings(value: Any) -> Any:
    """Trims every string, nested objects and lists included (keys and order are kept)."""
    if isinstance(value, str):
        return server_trim(value)
    if isinstance(value, Mapping):
        return {key: trim_strings(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [trim_strings(item) for item in value]
    return value


def required(value: str, field: str) -> str:
    """The trimmed value of a required field; raises when nothing is left (the API would answer 422)."""
    if not isinstance(value, str):
        raise DPayValueError(f"{field} must be a string")
    trimmed = server_trim(value)
    if trimmed == "":
        raise DPayValueError(f"{field} must not be empty")
    return trimmed


def sign_panel_body(checksum: ChecksumCalculator, body: Mapping[str, Any]) -> dict[str, Any]:
    """A panel (``/api/v1/pbl/*``) body ready to send: every string trimmed the way the API trims it, then
    signed with the ordered-body checksum over the values as sent."""
    trimmed: dict[str, Any] = trim_strings(body)
    trimmed["checksum"] = checksum.ordered_body(trimmed)
    return trimmed
