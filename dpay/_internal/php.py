from __future__ import annotations

import json
import math
from typing import Any


def is_php_int(value: Any) -> bool:
    return type(value) is int


def is_php_float(value: Any) -> bool:
    return type(value) is float


def is_php_bool(value: Any) -> bool:
    return type(value) is bool


def is_scalar(value: Any) -> bool:
    return type(value) in (int, float, bool, str)


def is_numeric(value: Any) -> bool:
    if type(value) in (int, float):
        return True
    if not isinstance(value, str):
        return False
    stripped = value.strip()
    if stripped == "":
        return False
    try:
        float(stripped)
    except ValueError:
        return False
    return True


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
    stripped = text.strip()
    index = 0
    if index < len(stripped) and stripped[index] in "+-":
        index += 1
    start = index
    while index < len(stripped) and stripped[index].isdigit():
        index += 1
    if index == start:
        return 0
    return int(stripped[:index])


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
