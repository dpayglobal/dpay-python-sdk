from __future__ import annotations

import pytest

from dpay import (
    ApplePayRequest,
    BlikAliasRegistration,
    BlikAliasType,
    CardData,
    CardRecurringRegistration,
    Currency,
    DccDecision,
    DeviceInfo,
    DPayValueError,
    InvoiceDetails,
    Money,
    Payer,
    PayoutInstruction,
    PayoutPosition,
    RedirectType,
    RegisterPaymentRequest,
    ReturnUrls,
    TransactionType,
)
from dpay.card.requests import CardPaymentRequest
from tests.scenario import build_device_info

URLS = ReturnUrls("https://a.pl/ok", "https://a.pl/fail", "https://a.pl/ipn")


def test_currency_accepts_any_three_uppercase_letters() -> None:
    Currency.assert_valid("GBP")
    assert Currency.is_valid("PLN")
    assert not Currency.is_valid("pln")
    assert not Currency.is_valid("PLNX")


def test_currency_error_message() -> None:
    with pytest.raises(DPayValueError, match='Invalid currency code "12A"'):
        Currency.assert_valid("12A")


@pytest.mark.parametrize("url", ["nope", "", "https://", "http://a b.pl"])
def test_return_urls_reject_invalid(url: str) -> None:
    with pytest.raises(DPayValueError, match="Invalid success URL"):
        ReturnUrls(url, "https://a.pl", "https://a.pl")


def test_return_urls_report_the_failing_field() -> None:
    with pytest.raises(DPayValueError, match="Invalid ipn URL"):
        ReturnUrls("https://a.pl", "https://a.pl", "nope")


def test_return_urls_ipn_is_optional() -> None:
    urls = ReturnUrls("https://a.pl/ok", "https://a.pl/fail")
    assert urls.ipn is None

    body = RegisterPaymentRequest.create(Money.pln(1), TransactionType.TRANSFERS, urls).to_api("s")
    assert "url_ipn" not in body
    assert list(body) == ["service", "value", "transactionType", "url_success", "url_fail"]


def test_transaction_types_after_removing_blik_recurring_and_bizum_direct() -> None:
    assert TransactionType.ALL == ("transfers", "dcb_gateway", "card_auth", "mb_way_direct", "card_recurring")
    for removed in ("blik_recurring", "bizum_direct"):
        with pytest.raises(DPayValueError, match=f'Invalid transaction type "{removed}"'):
            TransactionType.assert_valid(removed)
    assert not hasattr(TransactionType, "BLIK_RECURRING")
    assert not hasattr(TransactionType, "BIZUM_DIRECT")


def test_payer_validates_email() -> None:
    with pytest.raises(DPayValueError, match='Invalid email "nope"'):
        Payer.create().with_email("nope")


def test_transaction_type_is_validated_at_construction() -> None:
    with pytest.raises(DPayValueError, match='Invalid transaction type "nope"'):
        RegisterPaymentRequest.create(Money.pln(1), "nope", URLS)


def test_partner_platform_pattern() -> None:
    with pytest.raises(DPayValueError, match="Partner platform must match"):
        RegisterPaymentRequest.create(Money.pln(1), TransactionType.TRANSFERS, URLS).with_partner_platform(
            "lower"
        )


def test_blik_code_must_be_six_digits() -> None:
    with pytest.raises(DPayValueError, match="BLIK code must be exactly 6 digits"):
        RegisterPaymentRequest.create(Money.pln(1), TransactionType.TRANSFERS, URLS).with_blik_code(
            "12345", "ua", "ip"
        )


def test_blik_code_conflicts_with_alias() -> None:
    request = RegisterPaymentRequest.create(Money.pln(1), TransactionType.TRANSFERS, URLS)
    request.with_blik_alias("a-1", "ua", "ip")
    with pytest.raises(DPayValueError, match="blik_code cannot be combined with blik_alias"):
        request.with_blik_code("123456", "ua", "ip")


def test_blik_alias_conflicts_with_registration() -> None:
    request = RegisterPaymentRequest.create(Money.pln(1), TransactionType.TRANSFERS, URLS)
    request.with_register_blik_alias(BlikAliasRegistration("etykieta"))
    with pytest.raises(DPayValueError, match="blik_alias cannot be combined"):
        request.with_blik_alias("a-1", "ua", "ip")


def test_card_recurring_conflicts_are_symmetric() -> None:
    request = RegisterPaymentRequest.create(Money.pln(1), TransactionType.TRANSFERS, URLS)
    request.with_card_recurring_alias("al-1")
    with pytest.raises(DPayValueError, match="register_card_recurring cannot be combined"):
        request.with_card_recurring(CardRecurringRegistration.create("m"))

    other = RegisterPaymentRequest.create(Money.pln(1), TransactionType.TRANSFERS, URLS)
    other.with_card_recurring(CardRecurringRegistration.create("m"))
    with pytest.raises(DPayValueError, match="card_recurring_alias cannot be combined"):
        other.with_card_recurring_alias("al-1")


def test_efaktura_only_for_transfers() -> None:
    request = RegisterPaymentRequest.create(Money.pln(1), TransactionType.CARD_AUTH, URLS)
    with pytest.raises(DPayValueError, match="efaktura is allowed only"):
        request.with_efaktura()


def test_alias_ipn_url_is_validated() -> None:
    request = RegisterPaymentRequest.create(Money.pln(1), TransactionType.TRANSFERS, URLS)
    with pytest.raises(DPayValueError, match="Invalid alias IPN URL"):
        request.with_alias_ipn_url("nope")


def test_phone_number_sets_currency_too() -> None:
    request = RegisterPaymentRequest.create(Money.pln(1), TransactionType.TRANSFERS, URLS)
    request.with_phone_number("+48123", Currency.EUR)
    body = request.to_api("s")
    assert body["phone_number"] == "+48123"
    assert body["currency_code"] == "EUR"


def test_channel_flags_are_serialized_as_integers() -> None:
    request = RegisterPaymentRequest.create(Money.pln(1), TransactionType.TRANSFERS, URLS)
    request.with_credit_card(True).with_blik(False).with_accept_tos(True)
    body = request.to_api("s")
    assert body["creditcard"] == 1
    assert body["blik"] == 0
    assert body["accept_tos"] is True


def test_device_info_uses_uppercase_device_id_key() -> None:
    data = build_device_info().to_api()
    assert "deviceID" in data
    assert "deviceId" not in data
    assert data["browserJavaEnabled"] == "true"


def test_device_info_omits_java_flag_when_unset() -> None:
    device = DeviceInfo.create("a", "b", 1, 2, 3, 4, "ua", "os", "geo", "d", "app")
    assert "browserJavaEnabled" not in device.to_api()


@pytest.mark.parametrize("value", ["", "x" * 65])
def test_device_id_length(value: str) -> None:
    with pytest.raises(DPayValueError, match="Device ID must be 1-64 characters"):
        DeviceInfo.create("a", "b", 1, 2, 3, 4, "ua", "os", "geo", value, "app")


def test_application_name_length() -> None:
    with pytest.raises(DPayValueError, match="Application name must be 1-64 characters"):
        DeviceInfo.create("a", "b", 1, 2, 3, 4, "ua", "os", "geo", "d", "")


def test_invoice_due_date_format() -> None:
    with pytest.raises(DPayValueError, match="Payment due date must be in YYYY-MM-DD format"):
        InvoiceDetails.create().with_payment_due_date("15-08-2026")


def test_invoice_vat_amount_is_sent_in_minor_units() -> None:
    invoice = InvoiceDetails.create().with_vat_amount(Money.pln(560))
    assert invoice.to_api()["vat_amount"] == 560


def test_payout_requires_positions() -> None:
    with pytest.raises(DPayValueError, match="requires at least one position"):
        PayoutInstruction.create([])


def test_payout_rejects_foreign_positions() -> None:
    with pytest.raises(DPayValueError, match="Positions must be PayoutPosition instances"):
        PayoutInstruction.create(["nope"])


def test_payout_rejects_unknown_fee_mode() -> None:
    position = PayoutPosition("PL61", "tytul", Money.pln(1))
    with pytest.raises(DPayValueError, match='Invalid payout fee mode "brutto"'):
        PayoutInstruction.create([position], "brutto")


def test_payout_position_validates_iban_and_title() -> None:
    with pytest.raises(DPayValueError, match="Payout IBAN must not be empty"):
        PayoutPosition("", "tytul", Money.pln(1))
    with pytest.raises(DPayValueError, match="Payout title must be 1-255 characters"):
        PayoutPosition("PL61", "", Money.pln(1))


def test_payout_position_amount_is_a_float() -> None:
    assert PayoutPosition("PL61", "t", Money.pln(1050)).to_api()["amount"] == 10.50


def test_blik_alias_label_length() -> None:
    with pytest.raises(DPayValueError, match="Alias label must be 1-50 characters"):
        BlikAliasRegistration("x" * 51)


def test_blik_aliases_are_only_uid() -> None:
    # PAYID aliases are recurring payments - DPayClient.recurring
    assert BlikAliasType.ALL == ("UID",)
    assert BlikAliasRegistration("etykieta").to_api() == {"label": "etykieta", "type": "UID"}
    with pytest.raises(DPayValueError, match='Invalid BLIK alias type "PAYID"'):
        BlikAliasRegistration("etykieta", "PAYID")


def test_card_recurring_limits_use_minor_units() -> None:
    data = CardRecurringRegistration.create("m").with_limit_amt(Money.pln(20000)).to_api()
    assert data["limit_amt"] == 20000


def test_card_recurring_label_length() -> None:
    with pytest.raises(DPayValueError, match="Mandate label must be 1-50 characters"):
        CardRecurringRegistration.create("")


def test_card_recurring_frequency_is_validated() -> None:
    with pytest.raises(DPayValueError, match="Invalid card recurring frequency"):
        CardRecurringRegistration.create("m").with_frequency("EVERY_DAY")


@pytest.mark.parametrize("pan", ["4111", "41111111111111111111", "abcd1234efgh"])
def test_card_data_rejects_bad_pan(pan: str) -> None:
    with pytest.raises(DPayValueError, match="Card number must be 12-19 digits"):
        CardData(pan, "123", "12/25")


def test_card_data_strips_spaces_from_pan() -> None:
    assert CardData("4111 1111 1111 1111", "123", "12/25").pan == "4111111111111111"


def test_card_data_rejects_bad_cvv() -> None:
    with pytest.raises(DPayValueError, match="CVV must be 3-4 digits"):
        CardData("4111111111111111", "12", "12/25")


@pytest.mark.parametrize("expiry", ["13/25", "1/25", "12/2025", "00/25"])
def test_card_data_rejects_bad_expiry(expiry: str) -> None:
    with pytest.raises(DPayValueError, match="Expiry must be in MM/YY format"):
        CardData("4111111111111111", "123", expiry)


def test_card_data_repr_hides_secrets() -> None:
    text = repr(CardData("4111111111111111", "123", "12/25"))
    assert "4111111111111111" not in text
    assert "123" not in text
    assert "****1111" in text


def test_dcc_decision_is_validated() -> None:
    with pytest.raises(DPayValueError, match='Invalid DCC decision "maybe"'):
        CardPaymentRequest.create(build_device_info()).with_dcc_decision("maybe")


def test_dcc_decision_constants() -> None:
    assert DccDecision.ALL == ("accept", "reject")
    assert RedirectType.ALL == ("SUCCESS", "FORM", "URL", "DCC_OFFER")


def test_apple_pay_init_has_no_token() -> None:
    body = ApplePayRequest.init(build_device_info()).to_api()
    assert body["xPayType"] == "APPLE_PAY_INIT"
    assert "xPayToken" not in body


def test_apple_pay_pay_carries_token() -> None:
    body = ApplePayRequest.pay("tok", build_device_info()).to_api()
    assert body["xPayType"] == "APPLE_PAY"
    assert body["xPayToken"] == "tok"


def test_card_request_field_order() -> None:
    body = (
        CardPaymentRequest.create(build_device_info())
        .with_email("a@b.pl")
        .with_channel_id(1)
        .with_card_holder("Jan", "Kowalski")
        .with_encrypted_card_data("enc")
        .with_three_ds_confirmed(True)
        .with_dcc_decision(DccDecision.ACCEPT)
        .to_api()
    )
    assert list(body) == [
        "email",
        "channelId",
        "cardHolderFirstName",
        "cardHolderLastName",
        "encryptedCardData",
        "deviceInfo",
        "threeDsConfirmed",
        "dccDecision",
    ]


def test_validation_errors_are_also_value_errors() -> None:
    with pytest.raises(ValueError):
        Currency.assert_valid("nope")
