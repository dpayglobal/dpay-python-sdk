from __future__ import annotations

from typing import Literal

from dpay.exceptions import DPayValueError

RedirectTypeValue = Literal["SUCCESS", "FORM", "URL", "DCC_OFFER"]
DccDecisionValue = Literal["accept", "reject"]
CardRecurringOperationValue = Literal["add_card", "cof_initial", "charge"]


class RedirectType:
    SUCCESS = "SUCCESS"
    FORM = "FORM"
    URL = "URL"
    DCC_OFFER = "DCC_OFFER"

    ALL = (SUCCESS, FORM, URL, DCC_OFFER)

    @staticmethod
    def assert_valid(value: str) -> None:
        if value not in RedirectType.ALL:
            raise DPayValueError(f'Invalid redirect type "{value}"')


class DccDecision:
    ACCEPT = "accept"
    REJECT = "reject"

    ALL = (ACCEPT, REJECT)

    @staticmethod
    def assert_valid(value: str) -> None:
        if value not in DccDecision.ALL:
            raise DPayValueError(f'Invalid DCC decision "{value}"')


class CardRecurringOperation:
    ADD_CARD = "add_card"
    COF_INITIAL = "cof_initial"
    CHARGE = "charge"

    ALL = (ADD_CARD, COF_INITIAL, CHARGE)

    @staticmethod
    def assert_valid(value: str) -> None:
        if value not in CardRecurringOperation.ALL:
            raise DPayValueError(f'Invalid card recurring operation "{value}"')


class CardRecurringFrequency:
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    BIWEEKLY = "BIWEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    SEMIANNUAL = "SEMIANNUAL"
    ANNUAL = "ANNUAL"

    ALL = (DAILY, WEEKLY, BIWEEKLY, MONTHLY, QUARTERLY, SEMIANNUAL, ANNUAL)

    @staticmethod
    def assert_valid(value: str) -> None:
        if value not in CardRecurringFrequency.ALL:
            raise DPayValueError(f'Invalid card recurring frequency "{value}"')
