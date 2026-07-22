from __future__ import annotations

from typing import Any

from dpay._internal.php import is_scalar, php_strval


def _message(data: dict[str, Any]) -> str | None:
    value = data.get("message")
    return php_strval(value) if is_scalar(value) else None


class Refund:
    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw
        self.is_accepted = raw.get("status") == "success" and raw.get("refund", False) is True
        self.message = _message(raw)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Refund:
        return cls(data)


class RefundAvailability:
    def __init__(self, raw: dict[str, Any], http_status: int | None = None) -> None:
        self.raw = raw
        self.is_available = raw.get("refund", False) is True
        self.message = _message(raw)
        self.http_status = http_status

    @classmethod
    def from_api(cls, data: dict[str, Any], http_status: int | None = None) -> RefundAvailability:
        return cls(data, http_status)
