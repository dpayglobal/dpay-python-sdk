from __future__ import annotations

from typing import Any

from dpay._internal.php import is_scalar, php_strval
from dpay.blik.enums import BlikAliasType


def _scalar_string(raw: dict[str, Any], key: str, default: str) -> str:
    value = raw.get(key)
    return php_strval(value) if is_scalar(value) else default


def _strict_string(raw: dict[str, Any], key: str) -> str | None:
    value = raw.get(key)
    return value if isinstance(value, str) else None


class BlikApp:
    def __init__(self, key: str | None, label: str | None) -> None:
        self.key = key
        self.label = label

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> BlikApp:
        return cls(_strict_string(data, "key"), _strict_string(data, "label"))


class BlikAlias:
    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw
        self.alias_value = _scalar_string(raw, "alias_value", "")
        self.alias_type = _scalar_string(raw, "alias_type", BlikAliasType.UID)
        self.status = _strict_string(raw, "status")
        self.expiration_date = _strict_string(raw, "expiration_date")
        apps = raw.get("apps")
        apps = apps if isinstance(apps, list) else []
        self.apps = [BlikApp.from_api(app) for app in apps if isinstance(app, dict)]

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> BlikAlias:
        return cls(data)

    @property
    def is_active(self) -> bool:
        return self.status == "ACTIVE"
