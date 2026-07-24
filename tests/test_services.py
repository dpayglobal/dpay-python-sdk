from __future__ import annotations

import json

import pytest

from dpay import (
    ApiServerError,
    AuthenticationError,
    CardPaymentError,
    CardPaymentRequest,
    DPayClient,
    DPayValueError,
    Money,
    PaymentRejectedError,
    RegisterPaymentRequest,
    ReturnUrls,
    TransactionType,
)
from dpay.testing import MockHttpClient
from tests.conftest import SECRET, SERVICE
from tests.scenario import build_device_info

URLS = ReturnUrls("https://shop.test/ok", "https://shop.test/fail", "https://shop.test/ipn")


def _request() -> RegisterPaymentRequest:
    return RegisterPaymentRequest.create(Money.pln(1050), TransactionType.TRANSFERS, URLS)


def test_register_posts_to_payments_host(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, {"transactionId": "tx-1", "msg": "https://secure.dpay.pl/p/1"})
    payment = client.payments.register(_request())

    assert transport.last_request.url == "https://api-payments.dpay.pl/api/v1_0/payments/register"
    assert transport.last_request.headers["Content-Type"] == "application/json"
    assert payment.redirect_url == "https://secure.dpay.pl/p/1"
    assert payment.transaction_id == "tx-1"


def test_register_appends_checksum_last(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, {"transactionId": "tx-1", "msg": "ok"})
    client.payments.register(_request())
    assert list(transport.last_request_body)[-1] == "checksum"


def test_register_sends_amount_as_string(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, {"transactionId": "tx-1", "msg": "ok"})
    client.payments.register(_request())
    assert transport.last_request_body["value"] == "10.50"


def test_register_detects_paid_transaction(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, {"transactionId": "tx-1", "msg": "Transaction paid"})
    payment = client.payments.register(_request())
    assert payment.is_paid
    assert payment.redirect_url is None


def test_register_detects_internal_processing(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, {"transactionId": "tx-1", "msg": "Internal processing"})
    assert client.payments.register(_request()).is_internal_processing


def test_register_rejected_with_error_flag(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(
        200,
        {
            "error": True,
            "msg": "Rejected",
            "transactionId": "tx-9",
            "additionalInfo": {"error": "err05"},
        },
    )
    with pytest.raises(PaymentRejectedError) as error:
        client.payments.register(_request())
    assert error.value.http_status == 200
    assert error.value.error_code == "err05"
    assert error.value.transaction_id == "tx-9"


def test_register_rejected_with_status_false(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, {"status": False, "msg": "Rejected"})
    with pytest.raises(PaymentRejectedError):
        client.payments.register(_request())


def test_register_exposes_card_recurring_alias(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(
        200,
        {"transactionId": "tx-1", "msg": "ok", "additionalInfo": {"card_recurring_alias": "al-1"}},
    )
    assert client.payments.register(_request()).card_recurring_alias == "al-1"


def test_details_parses_refunds(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(
        200,
        {
            "transaction": {
                "id": "tx-1",
                "value": "29.99",
                "status": "paid",
                "refunded_amount": "5.00",
                "available_refund_amount": "24.99",
                "fully_refunded": False,
                "settled": True,
            },
            "payer": {"email": "jan@example.com"},
            "refunds": [{"payment_id": "r-1", "value": "5.00", "status": "paid"}, "junk"],
        },
    )
    transaction = client.payments.details("tx-1")

    assert transport.last_request.url == "https://panel.dpay.pl/api/v1/pbl/details"
    assert transaction.is_paid
    assert transaction.value.to_decimal() == "29.99"
    assert transaction.available_refund_amount.to_decimal() == "24.99"
    assert transaction.payer == {"email": "jan@example.com"}
    assert len(transaction.refunds) == 1
    assert transaction.refunds[0].payment_id == "r-1"


def test_details_treats_captured_as_paid(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, {"transaction": {"id": "t", "status": "captured"}})
    assert client.payments.details("t").is_paid


def test_details_survives_unknown_status(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, {"transaction": {"id": "t", "status": "brand_new"}})
    transaction = client.payments.details("t")
    assert transaction.status == "brand_new"
    assert not transaction.is_paid


def test_unparsable_amount_falls_back_to_zero(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, {"transaction": {"id": "t", "value": "not-a-number"}})
    assert client.payments.details("t").value.minor == 0


def test_invalid_json_raises_server_error(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_text(200, "not json")
    with pytest.raises(ApiServerError, match="Invalid JSON in API response"):
        client.payments.details("t")


def test_refund_body_order_matches_checksum(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, {"status": "success", "refund": True})
    client.refunds.create("tx-1", Money.pln(500), "powod")
    assert list(transport.last_request_body) == [
        "service",
        "transaction_id",
        "value",
        "reason",
        "checksum",
    ]


def test_refund_omits_optional_fields(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, {"status": "success", "refund": True})
    refund = client.refunds.create("tx-1")
    assert list(transport.last_request_body) == ["service", "transaction_id", "checksum"]
    assert refund.is_accepted


def test_refund_not_accepted(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, {"status": "error", "refund": False, "message": "nie"})
    refund = client.refunds.create("tx-1")
    assert not refund.is_accepted
    assert refund.message == "nie"


@pytest.mark.parametrize("status", [200, 400, 402, 406, 409, 410, 411])
def test_check_availability_returns_business_outcome(
    client: DPayClient, transport: MockHttpClient, status: int
) -> None:
    transport.queue_json(status, {"refund": False, "message": "nie mozna"})
    availability = client.refunds.check_availability("tx-1")
    assert not availability.is_available
    assert availability.http_status == status
    assert availability.message == "nie mozna"


def test_check_availability_business_401_is_not_an_error(
    client: DPayClient, transport: MockHttpClient
) -> None:
    transport.queue_json(401, {"refund": False, "message": "kanal nierefundowalny"})
    assert client.refunds.check_availability("tx-1").http_status == 401


def test_check_availability_checksum_401_raises(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(401, {"refund": False, "message": "Unauthorized request"})
    with pytest.raises(AuthenticationError):
        client.refunds.check_availability("tx-1")


def test_check_availability_without_refund_key_raises(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(500, {"message": "boom"})
    with pytest.raises(ApiServerError):
        client.refunds.check_availability("tx-1")


def test_banks_all_is_a_get_without_checksum(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, [{"id": "1", "name": "Bank", "test": True, "iterator": "3"}])
    banks = client.banks.all()

    assert transport.last_request.method == "GET"
    assert transport.last_request.body is None
    assert banks[0].id == "1"
    assert banks[0].is_test
    assert banks[0].iterator == 3


def test_banks_for_service_uses_given_timestamp(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, [])
    client.banks.for_service(1784700000)
    assert transport.last_request_body["timestamp"] == 1784700000


def test_banks_for_service_defaults_to_clock(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, [])
    client.banks.for_service()
    assert isinstance(transport.last_request_body["timestamp"], int)


def test_banks_skip_non_object_entries(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, [{"id": "1"}, "junk", 5])
    assert len(client.banks.all()) == 1


def test_payout_details_field_order_without_timestamp(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, {"id": 7, "state": 1})
    client.payouts.details(4242)
    assert list(transport.last_request_body) == ["service", "withdraw_id", "checksum"]


def test_payout_details_field_order_with_timestamp(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, {"id": 7, "state": 1})
    client.payouts.details(4242, 1784700000)
    assert list(transport.last_request_body) == [
        "service",
        "timestamp",
        "withdraw_id",
        "checksum",
    ]


def test_payout_details_states(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(
        200,
        {
            "id": 7,
            "state": -1,
            "net": 100.5,
            "fee": 2.0,
            "gross": 102.5,
            "direct_settlement": 1,
            "declined": "1",
            "receiver": {"nrb": "PL61", "amount": 10.0, "receiverName": "Jan"},
        },
    )
    details = client.payouts.details(1)

    assert details.is_failed and not details.is_waiting and not details.is_processed
    assert details.net.to_decimal() == "100.50"
    assert details.is_direct_settlement
    assert details.is_declined
    assert details.receiver is not None
    assert details.receiver.receiver_name == "Jan"
    assert details.receiver.amount is not None
    assert details.receiver.amount.to_decimal() == "10.00"


def test_blik_alias_checksum_covers_only_alias_value(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, {"data": {"alias_value": "a-1", "status": "ACTIVE"}})
    alias = client.blik.alias("a-1")

    body = transport.last_request_body
    assert list(body) == ["service", "alias_value", "alias_type", "checksum"]
    assert alias.is_active


def test_blik_unregister_keeps_reason_out_of_checksum(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, {"data": {}})
    transport.queue_json(200, {"data": {}})
    client.blik.unregister_alias("a-1")
    without_reason = transport.last_request_body["checksum"]
    client.blik.unregister_alias("a-1", reason="user request")
    with_reason = transport.last_request_body

    assert with_reason["reason"] == "user request"
    assert with_reason["checksum"] == without_reason


def test_blik_rejects_unknown_alias_type(client: DPayClient) -> None:
    with pytest.raises(DPayValueError, match='Invalid BLIK alias type "NOPE"'):
        client.blik.alias("a-1", "NOPE")


def test_blik_recurring_status_unwraps_envelope(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(
        200,
        {
            "data": {
                "alias_value": "a-1",
                "status": "ACTIVE",
                "registration": {"model": "M", "frequency": "1M", "limit_amt": 100},
            }
        },
    )
    status = client.blik.recurring_status("a-1")
    assert status.is_active
    assert status.registration is not None
    assert status.registration.model == "M"
    assert status.registration.limit_amt == 100


def test_card_public_key_is_trimmed(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_text(200, "  -----BEGIN PUBLIC KEY-----\nAAA\n-----END PUBLIC KEY-----\n  ")
    assert client.cards.public_key() == "-----BEGIN PUBLIC KEY-----\nAAA\n-----END PUBLIC KEY-----"


def test_card_path_encodes_transaction_id(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, {"success": True, "message": {"redirectType": "SUCCESS"}})
    client.cards.pay_otp("tx 1/2", CardPaymentRequest.create(build_device_info()))
    assert transport.last_request.url.endswith("/cards/payment/tx%201%2F2/pay/card-otp")


def test_card_capture_sends_amount(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, {"success": True, "message": {"redirectType": "SUCCESS"}})
    client.cards.capture("tx-1", Money.pln(2999))
    assert transport.last_request_body == {"amount": 29.99}


def test_card_business_failure_raises(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, {"success": False, "message": "DCC_OFFER_EXPIRED"})
    with pytest.raises(CardPaymentError) as error:
        client.cards.cancel("tx-1")
    assert error.value.http_status == 200
    assert error.value.error_code == "DCC_OFFER_EXPIRED"


def test_card_three_ds_form_is_base64_decoded(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(
        200,
        {"success": True, "message": {"redirectType": "FORM", "redirectText": "PGZvcm0+"}},
    )
    result = client.cards.pre_auth("tx-1", CardPaymentRequest.create(build_device_info()))
    assert result.requires_three_ds_form
    assert result.three_ds_form_html == "<form>"
    assert result.redirect_url is None


def test_card_redirect_url_is_base64_decoded(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(
        200,
        {
            "success": True,
            "message": {"redirectType": "URL", "redirectText": "aHR0cHM6Ly9hLnBs"},
        },
    )
    result = client.cards.pre_auth("tx-1", CardPaymentRequest.create(build_device_info()))
    assert result.redirect_url == "https://a.pl"


def test_card_invalid_base64_returns_none(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, {"success": True, "message": {"redirectType": "URL", "redirectText": "!!!"}})
    result = client.cards.pre_auth("tx-1", CardPaymentRequest.create(build_device_info()))
    assert result.redirect_url is None


def test_card_dcc_offer_is_parsed(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(
        200,
        {
            "success": True,
            "message": {
                "redirectType": "DCC_OFFER",
                "dccOffer": {
                    "currencyConversionId": "cc-1",
                    "originalAmount": 29.99,
                    "originalCurrency": "PLN",
                    "convertedAmount": 7.05,
                    "convertedCurrency": "EUR",
                    "exchangeRate": 4.2543,
                    "validUntil": "2026-07-22T12:00:00Z",
                    "declarationText": "Akceptuje",
                    "europeanEconomicArea": True,
                    "markup": [{"rate": 0.03, "additionalInfo": "marza"}],
                },
            },
        },
    )
    result = client.cards.pre_auth("tx-1", CardPaymentRequest.create(build_device_info()))
    offer = result.dcc_offer

    assert result.has_dcc_offer
    assert offer is not None
    assert offer.converted_amount.currency == "EUR"
    assert offer.converted_amount.to_decimal() == "7.05"
    assert offer.exchange_rate == 4.2543
    assert offer.markup[0].rate == 0.03


def test_empty_queue_is_an_assertion_error(client: DPayClient) -> None:
    with pytest.raises(AssertionError):
        client.banks.all()


def test_mock_last_request_body_requires_json(transport: MockHttpClient) -> None:
    transport.queue_text(200, "x")
    client = DPayClient(service=SERVICE, secret_hash=SECRET, http_client=transport)
    client.cards.public_key()
    with pytest.raises(AssertionError):
        _ = transport.last_request_body


def test_request_body_is_valid_json(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, {"transactionId": "t", "msg": "ok"})
    client.payments.register(_request())
    assert json.loads(transport.last_request.body or "")["service"] == SERVICE
