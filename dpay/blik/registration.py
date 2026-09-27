from __future__ import annotations

from dpay.blik.enums import BlikAliasType
from dpay.exceptions import DPayValueError


class BlikAliasRegistration:
    def __init__(self, label: str, type: str = BlikAliasType.UID) -> None:
        if label == "" or len(label) > 50:
            raise DPayValueError("Alias label must be 1-50 characters")
        BlikAliasType.assert_valid(type)
        self.label = label
        self.type = type

    def to_api(self) -> dict[str, str]:
        return {"label": self.label, "type": self.type}
