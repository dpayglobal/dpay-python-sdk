from __future__ import annotations

import base64
import binascii
from typing import Any

from dpay._internal.php import is_numeric, is_scalar, php_strval
from dpay.card.enums import RedirectType
from dpay.currency import Currency
from dpay.money import Money


def _strict_string(raw: dict[str, Any], key: str) -> str | None:
    value = raw.get(key)
    return value if isinstance(value, str) else None


def _scalar_string(raw: dict[str, Any], key: str) -> str:
    value = raw.get(key)
    return php_strval(value) if is_scalar(value) else ""


def _float_or_zero(raw: dict[str, Any], key: str) -> float:
    value = raw.get(key, 0)
    return float(value) if is_numeric(value) else 0.0


def _decode_base64(text: str) -> str | None:
    try:
        return base64.b64decode(text, validate=True).decode("utf-8", "replace")
    except (ValueError, binascii.Error):
        return None


class DccMarkup:
    def __init__(self, rate: float, additional_info: str | None) -> None:
        self.rate = rate
        self.additional_info = additional_info

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> DccMarkup:
        return cls(_float_or_zero(data, "rate"), _strict_string(data, "additionalInfo"))


class DccOffer:
    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw
        self.currency_conversion_id = _scalar_string(raw, "currencyConversionId")
        original_currency = raw.get("originalCurrency")
        converted_currency = raw.get("convertedCurrency")
        self.original_amount = Money.try_from_api_number(
            raw.get("originalAmount", 0),
            original_currency if isinstance(original_currency, str) else Currency.PLN,
        ) or Money.pln(0)
        self.converted_amount = Money.try_from_api_number(
            raw.get("convertedAmount", 0),
            converted_currency if isinstance(converted_currency, str) else Currency.PLN,
        ) or Money.pln(0)
        self.exchange_rate = _float_or_zero(raw, "exchangeRate")
        self.valid_until = _scalar_string(raw, "validUntil")
        self.declaration_text = _scalar_string(raw, "declarationText")
        self.is_european_economic_area = bool(raw.get("europeanEconomicArea", False))
        markup = raw.get("markup")
        markup = markup if isinstance(markup, list) else []
        self.markup = [DccMarkup.from_api(item) for item in markup if isinstance(item, dict)]

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> DccOffer:
        return cls(data)


class CardPaymentResult:
    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw
        message = raw.get("message")
        message = message if isinstance(message, dict) else {}
        self.redirect_type = _strict_string(message, "redirectType")
        redirect_text = _strict_string(message, "redirectText")
        self.redirect_text = redirect_text if redirect_text else None
        dcc_offer = message.get("dccOffer")
        self.dcc_offer = DccOffer.from_api(dcc_offer) if isinstance(dcc_offer, dict) else None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> CardPaymentResult:
        return cls(data)

    @property
    def is_success(self) -> bool:
        return self.redirect_type == RedirectType.SUCCESS

    @property
    def requires_three_ds_form(self) -> bool:
        return self.redirect_type == RedirectType.FORM

    @property
    def requires_redirect(self) -> bool:
        return self.redirect_type == RedirectType.URL

    @property
    def has_dcc_offer(self) -> bool:
        return self.redirect_type == RedirectType.DCC_OFFER

    @property
    def three_ds_form_html(self) -> str | None:
        if not self.requires_three_ds_form or self.redirect_text is None:
            return None
        return _decode_base64(self.redirect_text)

    @property
    def redirect_url(self) -> str | None:
        if not self.requires_redirect or self.redirect_text is None:
            return None
        return _decode_base64(self.redirect_text)
