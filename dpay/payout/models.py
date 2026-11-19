from __future__ import annotations

from typing import Any

from dpay._internal.php import is_numeric, is_php_int, is_scalar, php_int
from dpay.currency import Currency
from dpay.money import Money
from dpay.payout.enums import PayoutState


def _strict_string(raw: dict[str, Any], key: str) -> str | None:
    value = raw.get(key)
    return value if isinstance(value, str) else None


def _currency_code(raw: dict[str, Any]) -> str:
    currency = raw.get("currency_code")
    return currency if isinstance(currency, str) and Currency.is_valid(currency) else Currency.PLN


def _money(raw: dict[str, Any], key: str, currency: str = Currency.PLN) -> Money:
    return Money.try_from_api_number(raw.get(key, 0), currency) or Money(0, currency)


def _flag(raw: dict[str, Any], key: str) -> bool:
    # The API sends its 0/1 flags as JSON integers - only the integer 1 is true (not True, 1.0 or "1")
    value = raw.get(key)
    return is_php_int(value) and value == 1


def _numeric_int(raw: dict[str, Any], key: str, default: int) -> int:
    value = raw.get(key)
    return php_int(value) if is_numeric(value) else default


def _dict(raw: dict[str, Any], key: str) -> dict[str, Any]:
    value = raw.get(key)
    return value if isinstance(value, dict) else {}


class PayoutReceiver:
    def __init__(self, raw: dict[str, Any], currency: str = Currency.PLN) -> None:
        self.raw = raw
        self.currency = currency if Currency.is_valid(currency) else Currency.PLN

    @classmethod
    def from_api(cls, data: dict[str, Any], currency: str = Currency.PLN) -> PayoutReceiver:
        return cls(data, currency)

    @property
    def nrb(self) -> str | None:
        return _strict_string(self.raw, "nrb")

    @property
    def title(self) -> str | None:
        return _strict_string(self.raw, "title")

    @property
    def amount(self) -> Money | None:
        return Money.try_from_api_number(self.raw.get("amount"), self.currency)

    @property
    def service(self) -> str | None:
        return _strict_string(self.raw, "service")

    @property
    def receiver_name(self) -> str | None:
        return _strict_string(self.raw, "receiverName")

    @property
    def receiver_address(self) -> str | None:
        return _strict_string(self.raw, "receiverAddress")


class PayoutDetails:
    """Payout header: ``withdraws/details``, and ``settlement`` of ``withdraws/details/full``.

    Amounts are in ``currency`` - ``currency_code`` when the API sends it, otherwise PLN.
    """

    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw
        self.currency = _currency_code(raw)
        self.id = php_int(raw.get("id")) if is_scalar(raw.get("id")) else 0
        self.state = php_int(raw.get("state")) if is_scalar(raw.get("state")) else 0
        self.net = _money(raw, "net", self.currency)
        self.fee = _money(raw, "fee", self.currency)
        self.gross = _money(raw, "gross", self.currency)
        self.creation_date = _strict_string(raw, "creation_date")
        self.is_direct_settlement = _flag(raw, "direct_settlement")
        self.nrb = _strict_string(raw, "nrb")
        self.is_declined = _flag(raw, "declined")
        self.decline_reason = _strict_string(raw, "decline_reason")
        self.decline_status = _strict_string(raw, "decline_status")
        receiver = raw.get("receiver")
        self.receiver = (
            PayoutReceiver.from_api(receiver, self.currency) if isinstance(receiver, dict) else None
        )

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> PayoutDetails:
        return cls(data)

    @property
    def is_waiting(self) -> bool:
        return self.state == PayoutState.WAITING

    @property
    def is_processed(self) -> bool:
        return self.state == PayoutState.PROCESSED

    @property
    def is_failed(self) -> bool:
        return self.state == PayoutState.FAILED

    @property
    def export_date(self) -> str | None:
        """When the transfer was sent to the bank (``withdraws/details/full`` only); ``None`` until then."""
        return _strict_string(self.raw, "export_date")

    @property
    def is_paysafecard(self) -> bool:
        """Paysafecard payout (``paysafecard`` is the JSON integer 1; sent only for regular, non-direct
        settlements)."""
        return _flag(self.raw, "paysafecard")


class PageMeta:
    """``meta`` of a paginated payout response: the page returned, its size and the totals of the result."""

    def __init__(self, page: int, per_page: int, total: int, total_pages: int) -> None:
        # Page that was returned - echoed back even beyond the last page.
        self.page = page
        self.per_page = per_page
        # Number of items in the whole result.
        self.total = total
        # 0 when the result is empty.
        self.total_pages = total_pages

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> PageMeta:
        return cls(
            _numeric_int(data, "page", 1),
            _numeric_int(data, "per_page", 0),
            _numeric_int(data, "total", 0),
            _numeric_int(data, "total_pages", 0),
        )

    @property
    def has_more(self) -> bool:
        return self.page < self.total_pages


class PayoutListItem:
    """One payout of ``payouts.list()``.

    The account, receiver and decline reason are in ``payouts.details(id)``.
    """

    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw
        self.currency = _currency_code(raw)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> PayoutListItem:
        return cls(data)

    @property
    def id(self) -> int:
        """Use as ``withdraw_id`` in ``payouts.details()`` and ``payouts.details_full()``."""
        return _numeric_int(self.raw, "id", 0)

    @property
    def type(self) -> str | None:
        """standard, direct or paysafecard (``PayoutType``)."""
        return _strict_string(self.raw, "type")

    @property
    def state(self) -> int:
        """0 waiting, 1 processed, -1 failure (``PayoutState``)."""
        return _numeric_int(self.raw, "state", 0)

    @property
    def is_waiting(self) -> bool:
        return self.state == PayoutState.WAITING

    @property
    def is_processed(self) -> bool:
        return self.state == PayoutState.PROCESSED

    @property
    def is_failed(self) -> bool:
        return self.state == PayoutState.FAILED

    @property
    def net(self) -> Money:
        return _money(self.raw, "net", self.currency)

    @property
    def fee(self) -> Money:
        return _money(self.raw, "fee", self.currency)

    @property
    def gross(self) -> Money:
        return _money(self.raw, "gross", self.currency)

    @property
    def creation_date(self) -> str | None:
        return _strict_string(self.raw, "creation_date")

    @property
    def export_date(self) -> str | None:
        """When the transfer was sent to the bank; ``None`` until then."""
        return _strict_string(self.raw, "export_date")

    @property
    def is_declined(self) -> bool:
        """``declined`` is the JSON integer 1."""
        return _flag(self.raw, "declined")


class PayoutPage:
    """One page of ``payouts.list()``, newest payouts first."""

    def __init__(self, items: list[PayoutListItem], meta: PageMeta) -> None:
        self.items = items
        self.meta = meta

    @classmethod
    def from_api(cls, response: dict[str, Any]) -> PayoutPage:
        withdraws = response.get("withdraws")
        if isinstance(withdraws, dict):
            withdraws = list(withdraws.values())
        if not isinstance(withdraws, list):
            withdraws = []
        items = [PayoutListItem.from_api(item) for item in withdraws if isinstance(item, dict)]
        return cls(items, PageMeta.from_api(_dict(response, "meta")))

    @property
    def has_more(self) -> bool:
        return len(self.items) > 0 and self.meta.has_more


class SettlementPosition:
    """A payment settled by a payout (``transactions[]`` of ``withdraws/details/full``)."""

    def __init__(self, raw: dict[str, Any], currency: str) -> None:
        self.raw = raw
        self.currency = currency

    @classmethod
    def from_api(cls, data: dict[str, Any], currency: str) -> SettlementPosition:
        return cls(data, currency)

    @property
    def payment_id(self) -> str | None:
        """Payment ID - the same as in the IPN; ``None`` when unknown."""
        return _strict_string(self.raw, "payment_id")

    @property
    def date(self) -> str | None:
        """When the payment was made."""
        return _strict_string(self.raw, "date")

    @property
    def net(self) -> Money:
        """Amount credited to you."""
        return _money(self.raw, "net", self.currency)

    @property
    def fee(self) -> Money:
        """Commission charged on this payment."""
        return _money(self.raw, "fee", self.currency)

    @property
    def gross(self) -> Money:
        """Amount paid by the payer."""
        return _money(self.raw, "gross", self.currency)

    @property
    def service_id(self) -> int | None:
        value = self.raw.get("service_id")
        return value if is_php_int(value) else None

    @property
    def service_name(self) -> str | None:
        return _strict_string(self.raw, "service_name")

    @property
    def custom(self) -> str | None:
        """The ``custom`` value from the registration, as in the IPN."""
        return _strict_string(self.raw, "custom")

    @property
    def ipksef(self) -> str | None:
        """KSeF payment identifier of a payment settled with an e-invoice."""
        return _strict_string(self.raw, "ipksef")


class PayoutSettlement:
    """``payouts.details_full()``: the payout header, the totals of the WHOLE settlement and one page of the
    payments it settles. A payout of exactly one payment returns one position; a payout with unknown
    positions returns none.
    """

    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw
        # Payout header (state, amounts, currency, account or receiver, decline reason).
        self.settlement = PayoutDetails.from_api(_dict(raw, "settlement"))
        currency = self.settlement.currency
        transactions = raw.get("transactions")
        if isinstance(transactions, dict):
            transactions = list(transactions.values())
        if not isinstance(transactions, list):
            transactions = []
        # Positions of this page.
        self.positions = [
            SettlementPosition.from_api(item, currency) for item in transactions if isinstance(item, dict)
        ]
        self.meta = PageMeta.from_api(_dict(raw, "meta"))

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> PayoutSettlement:
        return cls(data)

    @property
    def summary_net(self) -> Money:
        """Net total of the whole settlement."""
        return _money(_dict(self.raw, "summary"), "net", self.settlement.currency)

    @property
    def summary_fee(self) -> Money:
        return _money(_dict(self.raw, "summary"), "fee", self.settlement.currency)

    @property
    def summary_gross(self) -> Money:
        return _money(_dict(self.raw, "summary"), "gross", self.settlement.currency)

    @property
    def summary_count(self) -> int:
        """Number of positions in the whole settlement."""
        return _numeric_int(_dict(self.raw, "summary"), "count", 0)
