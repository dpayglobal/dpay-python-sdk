from __future__ import annotations

from typing import Any

from dpay._internal.validation import assert_date
from dpay.card.enums import CardRecurringFrequency
from dpay.exceptions import DPayValueError
from dpay.money import Money


class CardRecurringRegistration:
    def __init__(self, label: str) -> None:
        if label == "" or len(label) > 50:
            raise DPayValueError("Mandate label must be 1-50 characters")
        self.label = label
        self.frequency: str | None = None
        self.limit_amt: Money | None = None
        self.tot_limit_amt: Money | None = None
        self.limit_amt_fixed: bool | None = None
        self.expiration_date: str | None = None
        self.init_date: str | None = None

    @classmethod
    def create(cls, label: str) -> CardRecurringRegistration:
        return cls(label)

    def with_frequency(self, frequency: str) -> CardRecurringRegistration:
        CardRecurringFrequency.assert_valid(frequency)
        self.frequency = frequency
        return self

    def with_limit_amt(self, limit_amt: Money) -> CardRecurringRegistration:
        self.limit_amt = limit_amt
        return self

    def with_tot_limit_amt(self, tot_limit_amt: Money) -> CardRecurringRegistration:
        self.tot_limit_amt = tot_limit_amt
        return self

    def with_limit_amt_fixed(self, fixed: bool) -> CardRecurringRegistration:
        self.limit_amt_fixed = fixed
        return self

    def with_expiration_date(self, expiration_date: str) -> CardRecurringRegistration:
        self.expiration_date = assert_date(expiration_date)
        return self

    def with_init_date(self, init_date: str) -> CardRecurringRegistration:
        self.init_date = assert_date(init_date)
        return self

    def to_api(self) -> dict[str, Any]:
        data: dict[str, Any] = {"label": self.label}
        if self.frequency is not None:
            data["frequency"] = self.frequency
        if self.limit_amt is not None:
            data["limit_amt"] = self.limit_amt.minor
        if self.tot_limit_amt is not None:
            data["tot_limit_amt"] = self.tot_limit_amt.minor
        if self.limit_amt_fixed is not None:
            data["is_limit_amt_fixed"] = self.limit_amt_fixed
        if self.expiration_date is not None:
            data["expiration_date"] = self.expiration_date
        if self.init_date is not None:
            data["init_date"] = self.init_date
        return data
