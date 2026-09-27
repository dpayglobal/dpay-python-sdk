from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from dpay._internal.php import is_php_int
from dpay._internal.validation import assert_date, byte_length, is_valid_url
from dpay.exceptions import DPayValueError

_FREQUENCY = re.compile(r"[1-9][0-9]{0,2}[DWMY]")


class RecurringRegistration:
    """The ``recurring_registration`` object - a recurring payment registered with a BLIK code payment.

    Models:

    - O (open): no frequency or limits, the merchant charges any amount within its active ranges;
    - A (automatic): fixed amount, frequency, total limit, start and expiry date - all required;
    - M (manual): the customer confirms every charge in the banking app; frequency and limits optional.
    """

    MODEL_A = "A"
    MODEL_M = "M"
    MODEL_O = "O"

    METHOD_BLIK = "blik"

    def __init__(self, label: str, model: str, terms_url: str) -> None:
        if label == "" or len(label) > 50:
            raise DPayValueError("Recurring payment label must be 1-50 characters")
        if model not in (self.MODEL_A, self.MODEL_M, self.MODEL_O):
            raise DPayValueError(f'Invalid recurring model "{model}"')
        if byte_length(terms_url) > 2048 or not is_valid_url(terms_url):
            raise DPayValueError(f'Invalid terms URL "{terms_url}"')
        self.label = label
        self.model = model
        # The merchant's terms the customer accepted (consent evidence).
        self.terms_url = terms_url
        self.alias: str | None = None
        self.terms_version: str | None = None
        self.methods: list[str] | None = None
        self.frequency: str | None = None
        self.limit_amt: int | None = None
        self.tot_limit_amt: int | None = None
        self.limit_amt_fixed: bool | None = None
        self.expiration_date: str | None = None
        self.init_date: str | None = None

    @classmethod
    def create(cls, label: str, model: str, terms_url: str) -> RecurringRegistration:
        return cls(label, model, terms_url)

    def with_alias(self, alias: str) -> RecurringRegistration:
        """Your own alias of the recurring payment (max 128 characters); without it dpay assigns one."""
        if alias == "" or byte_length(alias) > 128:
            raise DPayValueError("Recurring alias must be 1-128 characters")
        self.alias = alias
        return self

    def with_terms_version(self, terms_version: str) -> RecurringRegistration:
        if terms_version == "" or len(terms_version) > 64:
            raise DPayValueError("Terms version must be 1-64 characters")
        self.terms_version = terms_version
        return self

    def with_methods(self, methods: Sequence[str]) -> RecurringRegistration:
        """Payment methods of the recurring payment - today only ``blik``."""
        if isinstance(methods, str) or len(methods) == 0 or len(set(methods)) != len(methods):
            raise DPayValueError("Methods must be a non-empty list of distinct methods")
        for method in methods:
            if method != self.METHOD_BLIK:
                raise DPayValueError(f'Unsupported recurring method "{method}"')
        self.methods = list(methods)
        return self

    def with_frequency(self, frequency: str) -> RecurringRegistration:
        """Frequency like ``1M``, ``2W``, ``14D``, ``1Y`` (1-999 days, weeks, months or years)."""
        if not isinstance(frequency, str) or _FREQUENCY.fullmatch(frequency) is None:
            raise DPayValueError(f'Invalid recurring frequency "{frequency}"')
        self.frequency = frequency
        return self

    def with_limit_amt(self, limit_amt: int) -> RecurringRegistration:
        """Single payment limit in minor units (grosz)."""
        self.limit_amt = _assert_positive(limit_amt, "limit_amt")
        return self

    def with_tot_limit_amt(self, tot_limit_amt: int) -> RecurringRegistration:
        """Total limit of all payments in minor units (grosz)."""
        self.tot_limit_amt = _assert_positive(tot_limit_amt, "tot_limit_amt")
        return self

    def with_limit_amt_fixed(self, fixed: bool) -> RecurringRegistration:
        self.limit_amt_fixed = fixed
        return self

    def with_expiration_date(self, expiration_date: str) -> RecurringRegistration:
        """YYYY-MM-DD, after today and at most 10 years ahead."""
        self.expiration_date = assert_date(expiration_date)
        return self

    def with_init_date(self, init_date: str) -> RecurringRegistration:
        """YYYY-MM-DD, the first charge date (today or later)."""
        self.init_date = assert_date(init_date)
        return self

    def to_api(self) -> dict[str, Any]:
        self._assert_model_rules()

        data: dict[str, Any] = {"label": self.label}
        if self.alias is not None:
            data["alias"] = self.alias
        data["model"] = self.model
        if self.frequency is not None:
            data["frequency"] = self.frequency
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
        if self.methods is not None:
            data["methods"] = list(self.methods)
        data["terms_url"] = self.terms_url
        if self.terms_version is not None:
            data["terms_version"] = self.terms_version
        return data

    def _assert_model_rules(self) -> None:
        if self.model == self.MODEL_O:
            for field, value in (
                ("frequency", self.frequency),
                ("limit_amt", self.limit_amt),
                ("tot_limit_amt", self.tot_limit_amt),
                ("is_limit_amt_fixed", self.limit_amt_fixed),
            ):
                if value is not None:
                    raise DPayValueError(f"{field} is not allowed in recurring model O")
        if self.model == self.MODEL_A:
            for field, required in (
                ("frequency", self.frequency),
                ("limit_amt", self.limit_amt),
                ("tot_limit_amt", self.tot_limit_amt),
                ("expiration_date", self.expiration_date),
                ("init_date", self.init_date),
            ):
                if required is None:
                    raise DPayValueError(f"{field} is required in recurring model A")
            if self.limit_amt_fixed is False:
                raise DPayValueError("Recurring model A requires a fixed amount (is_limit_amt_fixed = true)")


def _assert_positive(value: int, field: str) -> int:
    if not is_php_int(value) or value < 1:
        raise DPayValueError(f"{field} must be at least 1 (minor units)")
    return value
