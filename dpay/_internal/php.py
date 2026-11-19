from __future__ import annotations

import json
import math
import re
from typing import Any

# PHP 8 numeric strings: optional leading and trailing whitespace " \t\n\r\v\f" (not Unicode spaces), ASCII
# digits only (not Unicode digits, "_" separators, "inf" or "nan" that Python's float() and int() accept)
_PHP_WHITESPACE = "[ \t\n\r\x0b\x0c]*"
_PHP_NUMBER = r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?"
_NUMERIC_STRING = re.compile(f"{_PHP_WHITESPACE}{_PHP_NUMBER}{_PHP_WHITESPACE}")
_LEADING_NUMBER = re.compile(f"{_PHP_WHITESPACE}({_PHP_NUMBER})")
_INTEGER = re.compile(r"[+-]?[0-9]+")
_INT_MAX = 2**63 - 1
_INT_MIN = -(2**63)


def is_php_int(value: Any) -> bool:
    return type(value) is int


def is_php_float(value: Any) -> bool:
    return type(value) is float


def is_php_bool(value: Any) -> bool:
    return type(value) is bool


def is_scalar(value: Any) -> bool:
    return type(value) in (int, float, bool, str)


def is_numeric(value: Any) -> bool:
    """PHP 8 ``is_numeric()``."""
    if type(value) in (int, float):
        return True
    return isinstance(value, str) and _NUMERIC_STRING.fullmatch(value) is not None


def php_strval(value: Any) -> str:
    if value is None:
        return ""
    if type(value) is bool:
        return "1" if value else ""
    if type(value) is int:
        return str(value)
    if type(value) is float:
        return _float_to_php_string(value)
    if isinstance(value, str):
        return value
    return str(value)


def _float_to_php_string(value: float) -> str:
    if math.isnan(value):
        return "NAN"
    if math.isinf(value):
        return "INF" if value > 0 else "-INF"
    formatted = f"{value:.14G}"
    if "E" in formatted:
        mantissa, exponent = formatted.split("E")
        if "." not in mantissa:
            mantissa += ".0"
        sign = exponent[0]
        digits = exponent[1:].lstrip("0") or "0"
        return f"{mantissa}E{sign}{digits}"
    return formatted


def php_round(value: float) -> int:
    if value >= 0:
        return math.floor(value + 0.5)
    return math.ceil(value - 0.5)


def php_int(value: Any) -> int:
    if value is None:
        return 0
    if type(value) is bool:
        return 1 if value else 0
    if type(value) is int:
        return value
    if type(value) is float:
        if math.isnan(value) or math.isinf(value):
            return 0
        return math.trunc(value)
    if isinstance(value, str):
        return _leading_int(value)
    return 0


def _leading_int(text: str) -> int:
    """PHP 8 ``(int) $string`` (64-bit): the leading numeric part, saturated at the integer limits; a float
    part is truncated, an infinite one gives 0."""
    match = _LEADING_NUMBER.match(text)
    if match is None:
        return 0
    number = match.group(1)
    if _INTEGER.fullmatch(number) is not None:
        return max(_INT_MIN, min(_INT_MAX, int(number)))
    parsed = float(number)
    if math.isinf(parsed):
        return 0
    return max(_INT_MIN, min(_INT_MAX, math.trunc(parsed)))


_SAFE_INTEGRAL_FLOAT = 2**53


def _normalize_floats(value: Any) -> Any:
    if type(value) is float:
        if value.is_integer() and abs(value) < _SAFE_INTEGRAL_FLOAT:
            return int(value)
        return value
    if isinstance(value, dict):
        return {key: _normalize_floats(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize_floats(item) for item in value]
    return value


def php_json_encode(data: Any, *, escape_slashes: bool = False) -> str:
    encoded = json.dumps(_normalize_floats(data), ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    if escape_slashes:
        encoded = encoded.replace("/", "\\/")
    return encoded
