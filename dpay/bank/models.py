from __future__ import annotations

from typing import Any

from dpay._internal.php import is_scalar, php_int, php_strval


class Bank:
    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw
        self.id = php_strval(raw.get("id")) if is_scalar(raw.get("id")) else ""
        self.name = php_strval(raw.get("name")) if is_scalar(raw.get("name")) else ""
        self.image = raw["image"] if isinstance(raw.get("image"), str) else None
        on_from = raw.get("on_from", 0)
        self.on_from = php_int(on_from) if is_scalar(on_from) else 0
        on_to = raw.get("on_to", 0)
        self.on_to = php_int(on_to) if is_scalar(on_to) else 0
        iterator = raw.get("iterator")
        self.iterator = php_int(iterator) if is_scalar(iterator) else None
        test = raw.get("test", False)
        self.is_test = _php_bool(test) if is_scalar(test) else False
        self.type = raw["type"] if isinstance(raw.get("type"), str) else None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Bank:
        return cls(data)


def _php_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value not in ("", "0")
    return bool(value)
