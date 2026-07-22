from __future__ import annotations

import re
from typing import Any

from dpay._internal.validation import assert_date
from dpay.blik.enums import BlikAliasType
from dpay.exceptions import DPayValueError
from dpay.money import Money

_FREQUENCY = re.compile(r"^[1-9][0-9]{0,2}[DWMQY]$")
_MODELS = ("A", "M", "O")


class BlikAliasRegistration:
    def __init__(self, label: str, type: str = BlikAliasType.UID) -> None:
        if label == "" or len(label) > 50:
            raise DPayValueError("Alias label must be 1-50 characters")
        BlikAliasType.assert_valid(type)
        self.label = label
        self.type = type

    def to_api(self) -> dict[str, str]:
        return {"label": self.label, "type": self.type}


class BlikRecurringRegistration:
    def __init__(self, label: str, model: str, frequency: str) -> None:
        if label == "" or len(label) > 50:
            raise DPayValueError("Alias label must be 1-50 characters")
        if model not in _MODELS:
            raise DPayValueError(f'Invalid recurring model "{model}"')
        if _FREQUENCY.match(frequency) is None:
            raise DPayValueError(f'Invalid recurring frequency "{frequency}"')
        self.label = label
        self.model = model
        self.frequency = frequency
        self.value: Money | None = None
        self.limit_amt: int | None = None
        self.tot_limit_amt: int | None = None
        self.limit_amt_fixed: bool | None = None
        self.expiration_date: str | None = None
        self.init_date: str | None = None

    @classmethod
    def create(cls, label: str, model: str, frequency: str) -> BlikRecurringRegistration:
        return cls(label, model, frequency)

    def with_value(self, value: Money) -> BlikRecurringRegistration:
        self.value = value
        return self

    def with_limit_amt(self, limit_amt: int) -> BlikRecurringRegistration:
        self.limit_amt = limit_amt
        return self

    def with_tot_limit_amt(self, tot_limit_amt: int) -> BlikRecurringRegistration:
        self.tot_limit_amt = tot_limit_amt
        return self

    def with_limit_amt_fixed(self, fixed: bool) -> BlikRecurringRegistration:
        self.limit_amt_fixed = fixed
        return self

    def with_expiration_date(self, expiration_date: str) -> BlikRecurringRegistration:
        self.expiration_date = assert_date(expiration_date)
        return self

    def with_init_date(self, init_date: str) -> BlikRecurringRegistration:
        self.init_date = assert_date(init_date)
        return self

    def to_api(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "label": self.label,
            "type": BlikAliasType.PAYID,
            "model": self.model,
            "frequency": self.frequency,
        }
        if self.value is not None:
            data["value"] = self.value.to_decimal()
        if self.limit_amt is not None:
            data["limit_amt"] = self.limit_amt
        if self.tot_limit_amt is not None:
            data["tot_limit_amt"] = self.tot_limit_amt
        if self.limit_amt_fixed is not None:
            data["is_limit_amt_fixed"] = self.limit_amt_fixed
        if self.expiration_date is not None:
            data["expiration_date"] = self.expiration_date
        if self.init_date is not None:
            data["init_date"] = self.init_date
        return data
