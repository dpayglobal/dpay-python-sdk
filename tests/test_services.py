from __future__ import annotations

import base64
import hashlib
import json

import pytest

from dpay import (
    ApiServerError,
    ApplePayRequest,
    AuthenticationError,
    CardPaymentError,
    CardPaymentRequest,
    Currency,
    DPayClient,
    DPayValueError,
    InvalidRequestError,
    Money,
    NotFoundError,
    Payer,
    PaymentRejectedError,
    RegisteredTransaction,
    RegisterPaymentRequest,
    ReturnUrls,
    Transaction,
    TransactionType,
)
from dpay.refund.service import RefundService
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
    assert error.value.error_description is None


def test_register_rejection_carries_the_error_description(
    client: DPayClient, transport: MockHttpClient
) -> None:
    transport.queue_json(
        200,
        {
            "error": True,
            "msg": "Transaction canceled",
            "status": False,
            "transactionId": "tx-9",
            "additionalInfo": {"error": "INSUFFICIENT_FUNDS", "error_description": "IssId: 1"},
        },
    )
    with pytest.raises(PaymentRejectedError) as error:
        client.payments.register(_request())
    assert error.value.error_code == "INSUFFICIENT_FUNDS"
    assert error.value.error_description == "IssId: 1"


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


def test_blik_recurring_status_moved_to_recurring_service(client: DPayClient) -> None:
    # blik/recurring/status was removed from the API - client.recurring.status() replaces it
    assert not hasattr(client.blik, "recurring_status")
    assert callable(client.recurring.status)


def test_card_public_key_is_trimmed(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_text(200, "  -----BEGIN PUBLIC KEY-----\nAAA\n-----END PUBLIC KEY-----\n  ")
    assert client.cards.public_key() == "-----BEGIN PUBLIC KEY-----\nAAA\n-----END PUBLIC KEY-----"


def test_card_path_encodes_transaction_id(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, {"success": True, "message": {"redirectType": "SUCCESS"}})
    client.cards.pay_otp("tx 1/2", CardPaymentRequest.create(build_device_info()))
    assert transport.last_request.url.endswith("/cards/payment/tx%201%2F2/pay/card-otp")


def _shop_client(transport: MockHttpClient) -> DPayClient:
    return DPayClient(service="MyShop", secret_hash="secret123", http_client=transport)


def test_card_capture_signs_the_operation(transport: MockHttpClient) -> None:
    transport.queue_json(200, {"success": True, "status": "success", "message": {"redirectType": "SUCCESS"}})
    result = _shop_client(transport).cards.capture("TX-1", Money.pln(5999))

    assert result.is_success
    assert transport.last_request.url == "https://api-payments.dpay.pl/api/v1_0/cards/payment/TX-1/capture"
    # sha256(capture|service|transaction_id|amount|hash)
    assert transport.last_request.body == (
        '{"service":"MyShop","amount":59.99,'
        '"checksum":"f9f3713764216075a7e1e56a10baa695f802929e70453a0b68146d56d5d3c925"}'
    )


def test_card_cancel_without_amount_signs_an_empty_amount(transport: MockHttpClient) -> None:
    transport.queue_json(200, {"success": True, "status": "success", "message": {"redirectType": "SUCCESS"}})
    _shop_client(transport).cards.cancel("TX-1")

    assert (
        transport.last_request.url == "https://api-payments.dpay.pl/api/v1_0/cards/payment/TX-1/cancellation"
    )
    # sha256(cancellation|service|transaction_id||hash) - empty amount segment
    assert transport.last_request.body == (
        '{"service":"MyShop","checksum":"adde47e5fce49c92912d41cb34f44b363c6fe426f0c14aa3b5f58a061c7f4c4c"}'
    )


def test_card_cancel_with_amount_signs_two_decimals(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, {"success": True, "message": {"redirectType": "SUCCESS"}})
    client.cards.cancel("tx-1", Money.pln(3000))

    body = transport.last_request_body
    assert list(body) == ["service", "amount", "checksum"]
    assert body["amount"] == 30
    expected = hashlib.sha256(f"cancellation|{SERVICE}|tx-1|30.00|{SECRET}".encode()).hexdigest()
    assert body["checksum"] == expected


def test_card_checksum_uses_the_raw_transaction_id(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, {"success": True, "message": {"redirectType": "SUCCESS"}})
    client.cards.capture("tx 1/2", Money.pln(100))

    assert transport.last_request.url.endswith("/cards/payment/tx%201%2F2/capture")
    expected = hashlib.sha256(f"capture|{SERVICE}|tx 1/2|1.00|{SECRET}".encode()).hexdigest()
    assert transport.last_request_body["checksum"] == expected


def test_card_capture_error_code_comes_from_code(transport: MockHttpClient) -> None:
    transport.queue_json(
        401,
        {"success": False, "status": "error", "code": "INVALID_CHECKSUM", "message": "Invalid checksum"},
    )
    with pytest.raises(AuthenticationError) as error:
        _shop_client(transport).cards.capture("TX-1", Money.pln(100))
    assert error.value.error_code == "INVALID_CHECKSUM"


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


# 0.3.0 - refunds


def test_refund_message_id_goes_to_the_header_not_the_checksum(transport: MockHttpClient) -> None:
    transport.queue_json(200, {"status": "success", "refund": True, "message": "dpay.pl zwrot RET-2026-0001"})
    refund = _shop_client(transport).refunds.create(
        "30D9493D-1D73-3FBD-A5D4-633723CC7A68", None, None, None, "RET-2026-0001"
    )

    assert refund.message == "dpay.pl zwrot RET-2026-0001"
    assert transport.last_request.headers[RefundService.MESSAGE_ID_HEADER] == "RET-2026-0001"
    assert RefundService.MESSAGE_ID_HEADER == "DigitalPayments-PSP-Message-ID"
    body = transport.last_request_body
    assert list(body) == ["service", "transaction_id", "checksum"]
    assert body["checksum"] == "3b345f55900ae6a43220dd14a3827ed9a26a02a3eb46b856d302e2baa44b48a4"


def test_refund_without_message_id_sends_no_header(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, {"status": "success", "refund": True, "message": "dpay.pl TX"})
    client.refunds.create("TX-1")
    assert "DigitalPayments-PSP-Message-ID" not in transport.last_request.headers


def test_refund_message_id_keeps_the_shared_vector_checksum() -> None:
    from tests import api_vectors

    transport = MockHttpClient()
    client = DPayClient(
        service=api_vectors.SERVICE, secret_hash=api_vectors.SECRET_HASH, http_client=transport
    )
    transport.queue_json(200, {"status": "success", "refund": True})
    client.refunds.create(api_vectors.TRANSACTION_ID, message_id="RET-2026-0001")
    expected = api_vectors.vector(api_vectors.ORDERED_BODY, "refund_full")["checksum"]
    assert transport.last_request_body["checksum"] == expected


@pytest.mark.parametrize(
    "message_id",
    ["", "   ", "RET\r\nX-Evil: 1", "ZWROT-ŁÓDŹ", "RET-1\n", "RET\t1"],
    ids=["empty", "spaces-only", "line-break", "non-ascii", "trailing-newline", "tab"],
)
def test_invalid_refund_message_id_is_rejected(
    client: DPayClient, transport: MockHttpClient, message_id: str
) -> None:
    with pytest.raises(DPayValueError, match="Refund message ID must be non-empty printable ASCII"):
        client.refunds.create("TX-1", message_id=message_id)
    assert transport.requests == []


def test_long_refund_message_id_is_sent_whole(client: DPayClient, transport: MockHttpClient) -> None:
    # The API keeps the first 24 bytes - no client-side limit
    transport.queue_json(200, {"status": "success", "refund": True})
    client.refunds.create("TX-1", message_id="R" * 40)
    assert transport.last_request.headers["DigitalPayments-PSP-Message-ID"] == "R" * 40


def test_availability_buyer_support_refusal_on_423_is_an_outcome(
    client: DPayClient, transport: MockHttpClient
) -> None:
    transport.queue_json(
        423,
        {
            "status": "error",
            "refund": False,
            "code": "BUYER_SUPPORT_REFUND_NOT_APPLICABLE",
            "message": "Zwrot przez BOK dpay",
        },
    )
    availability = client.refunds.check_availability("TX-1")
    assert availability.is_available is False
    assert availability.http_status == 423


def test_availability_server_error_with_refund_key_raises(
    client: DPayClient, transport: MockHttpClient
) -> None:
    transport.queue_json(500, {"status": "error", "refund": False, "message": "Server error"})
    with pytest.raises(ApiServerError):
        client.refunds.check_availability("TX-1")


def test_availability_without_refund_key_raises(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(404, {"message": "Not Found"})
    with pytest.raises(NotFoundError):
        client.refunds.check_availability("TX-1")
    transport.queue_json(422, {"message": "The given data was invalid.", "errors": {"value": ["x"]}})
    with pytest.raises(InvalidRequestError):
        client.refunds.check_availability("TX-1")


def test_availability_checksum_401_raises_but_business_401_answers(
    client: DPayClient, transport: MockHttpClient
) -> None:
    transport.queue_json(401, {"refund": False, "message": "Unauthorized request"})
    with pytest.raises(AuthenticationError):
        client.refunds.check_availability("TX-1")
    transport.queue_json(
        401, {"refund": False, "message": "Transakcji dokonanych kanałami paysafecard nie można zwrócić"}
    )
    assert client.refunds.check_availability("TX-1").http_status == 401


# 0.3.0 - cards


def test_card_decline_at_http_200_carries_card_error(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(
        200,
        {
            "success": False,
            "status": "error",
            "message": "Payment declined",
            "error": {"code": "payment_declined", "declineCode": "05", "declineMessage": "Do not honor"},
        },
    )
    with pytest.raises(CardPaymentError) as error:
        client.cards.pay_otp("TX-1", CardPaymentRequest.create(build_device_info()))
    assert error.value.error_code == "Payment declined"
    assert error.value.http_status == 200
    card_error = error.value.card_error
    assert card_error is not None
    assert (card_error.code, card_error.decline_code, card_error.decline_message) == (
        "payment_declined",
        "05",
        "Do not honor",
    )


def test_card_decline_without_error_object_has_no_card_error(
    client: DPayClient, transport: MockHttpClient
) -> None:
    transport.queue_json(200, {"success": False, "status": "error", "message": "DCC_OFFER_EXPIRED"})
    with pytest.raises(CardPaymentError) as error:
        client.cards.pay_otp("TX-1", CardPaymentRequest.create(build_device_info()))
    assert error.value.error_code == "DCC_OFFER_EXPIRED"
    assert error.value.card_error is None


def test_apple_pay_init_returns_the_merchant_session(client: DPayClient, transport: MockHttpClient) -> None:
    session = {"epochTimestamp": 1790503500000, "merchantSessionIdentifier": "SSH-1", "signature": "abc"}
    transport.queue_json(
        200,
        {
            "success": True,
            "status": "success",
            "message": {
                "redirectType": "FORM",
                "redirectText": base64.b64encode(json.dumps(session).encode()).decode(),
            },
        },
    )
    result = client.cards.apple_pay("TX-1", ApplePayRequest.init(build_device_info()))
    assert result.apple_pay_merchant_session == session
    assert "email" not in transport.last_request_body


def test_apple_pay_merchant_session_vectors(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(
        200,
        {
            "success": True,
            "message": {
                "redirectType": "FORM",
                "redirectText": "eyJlcG9jaFRpbWVzdGFtcCI6MTc5MDUwMzUwMDAwMCwibWVyY2hhbnRTZXNzaW9uSWRlbnRpZmllciI6IlNTSC0xIn0=",
            },
        },
    )
    result = client.cards.apple_pay("TX-1", ApplePayRequest.init(build_device_info()))
    assert result.apple_pay_merchant_session == {
        "epochTimestamp": 1790503500000,
        "merchantSessionIdentifier": "SSH-1",
    }


def test_merchant_session_is_none_for_a_three_ds_form(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(
        200,
        {
            "success": True,
            "status": "success",
            "message": {"redirectType": "FORM", "redirectText": "PGZvcm0gbWV0aG9kPSJQT1NUIj48L2Zvcm0+"},
        },
    )
    result = client.cards.pay_otp("TX-1", CardPaymentRequest.create(build_device_info()))
    assert result.apple_pay_merchant_session is None
    assert result.three_ds_form_html == '<form method="POST"></form>'


@pytest.mark.parametrize(
    "message",
    [
        {"redirectType": "FORM", "redirectText": base64.b64encode(b"[1,2]").decode()},
        {"redirectType": "FORM", "redirectText": base64.b64encode(b'{"a":"\xff"}').decode()},
        {"redirectType": "URL", "redirectText": base64.b64encode(b'{"a":1}').decode()},
        {"redirectType": "FORM", "redirectText": "not base64!"},
        {"redirectType": "SUCCESS"},
    ],
    ids=["json-list", "invalid-utf8", "url-redirect", "invalid-base64", "success"],
)
def test_merchant_session_needs_a_json_object_in_a_form(
    client: DPayClient, transport: MockHttpClient, message: dict[str, str]
) -> None:
    transport.queue_json(200, {"success": True, "message": message})
    result = client.cards.apple_pay("TX-1", ApplePayRequest.init(build_device_info()))
    assert result.apple_pay_merchant_session is None


def test_apple_pay_sends_the_email_first(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, {"success": True, "status": "success", "message": {"redirectType": "SUCCESS"}})
    client.cards.apple_pay(
        "TX-1",
        ApplePayRequest.pay("APPLE-TOKEN", build_device_info())
        .with_email("client@example.com")
        .with_channel_id(31),
    )
    body = transport.last_request_body
    assert list(body) == ["email", "channelId", "xPayType", "xPayToken", "deviceInfo"]
    assert body["email"] == "client@example.com"
    assert body["xPayType"] == "APPLE_PAY"


# 0.3.0 - payments


def test_register_paid_returns_the_paid_transaction(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(
        200,
        {
            "error": False,
            "msg": "Transaction paid",
            "status": True,
            "transactionId": "30D9493D-1D73-3FBD-A5D4-633723CC7A68",
            "additionalInfo": {
                "transaction": {
                    "payment_id": "30D9493D-1D73-3FBD-A5D4-633723CC7A68",
                    "pid": None,
                    "mtid": None,
                    "email": "client@example.com",
                    "description": "Zamowienie #1234",
                    "name": "Jan",
                    "surname": "Kowalski",
                    "value": "10.00",
                    "status": "paid",
                    "creation_date": "2026-11-18 10:00:00",
                    "payment_date": "2026-11-18 10:01:00",
                }
            },
        },
    )
    transaction = client.payments.register(_request()).paid_transaction

    assert transaction is not None
    assert transaction.payment_id == "30D9493D-1D73-3FBD-A5D4-633723CC7A68"
    assert transaction.status == RegisteredTransaction.STATUS_PAID
    assert transaction.is_paid
    assert transaction.value == Money.pln(1000)
    assert transaction.email == "client@example.com"
    assert transaction.name == "Jan"
    assert transaction.surname == "Kowalski"
    assert transaction.pid is None
    assert transaction.payment_date == "2026-11-18 10:01:00"


def test_register_without_extras_has_no_paid_transaction_or_multibanco(
    client: DPayClient, transport: MockHttpClient
) -> None:
    transport.queue_json(200, {"transactionId": "tx-1", "msg": "Transaction paid"})
    payment = client.payments.register(_request())
    assert payment.paid_transaction is None
    assert payment.multibanco is None


def test_register_multibanco_returns_the_reference(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(
        200,
        {
            "error": False,
            "msg": "https://secure.dpay.pl/transfer@pay@ABC",
            "status": True,
            "transactionId": "ABC",
            "multibanco": {
                "entity": "12345",
                "reference": "123456789",
                "amount": "12.50",
                "currency": "EUR",
                "expires_at": "2026-11-21T10:00:00+00:00",
            },
        },
    )
    request = (
        RegisterPaymentRequest.create(
            Money.of(1250, Currency.EUR),
            TransactionType.TRANSFERS,
            ReturnUrls("https://shop.example/ok", "https://shop.example/fail"),
        )
        .with_channel("390")
        .with_payer(Payer.create().with_email("client@example.com").with_name("Joao", "Silva"))
        .with_accept_tos(True)
    )
    payment = client.payments.register(request)

    assert transport.last_request_body["currency_code"] == "EUR"
    multibanco = payment.multibanco
    assert multibanco is not None
    assert multibanco.entity == "12345"
    assert multibanco.reference == "123456789"
    assert multibanco.amount == Money.of(1250, "EUR")
    assert multibanco.currency == "EUR"
    assert multibanco.expires_at == "2026-11-21T10:00:00+00:00"
    assert payment.currency == "EUR"


def test_paid_transaction_value_uses_the_request_currency(
    client: DPayClient, transport: MockHttpClient
) -> None:
    transport.queue_json(
        200,
        {
            "msg": "Transaction paid",
            "additionalInfo": {"transaction": {"value": "10.00", "status": "captured"}},
        },
    )
    request = RegisterPaymentRequest.create(Money.of(1000, Currency.CZK), TransactionType.TRANSFERS, URLS)
    transaction = client.payments.register(request).paid_transaction
    assert transaction is not None
    assert transaction.value == Money.of(1000, "CZK")
    assert transaction.is_paid


def _transaction_fixture(**fields: object) -> Transaction:
    return Transaction.from_api({"transaction": {"id": "x", "value": "1.00", "status": "paid", **fields}})


def test_transaction_maps_fees_and_urls() -> None:
    transaction = _transaction_fixture(
        rate=2,
        minimal_fee=20,
        permanent_fee=0,
        urls={
            "success": "https://shop.example/ok",
            "fail": "https://shop.example/fail",
            "ipn": "https://shop.example/ipn",
        },
    )
    assert transaction.rate == "2"
    assert transaction.minimal_fee == 20
    assert transaction.permanent_fee == 0
    urls = transaction.urls
    assert urls is not None
    assert (urls.success, urls.fail, urls.ipn) == (
        "https://shop.example/ok",
        "https://shop.example/fail",
        "https://shop.example/ipn",
    )


def test_transaction_fees_from_database_strings_and_missing_ipn() -> None:
    transaction = _transaction_fixture(
        rate="1.49", minimal_fee="30", urls={"success": "https://shop.example/ok", "fail": "", "ipn": None}
    )
    assert transaction.rate == "1.49"
    assert transaction.minimal_fee == 30
    assert transaction.permanent_fee is None
    urls = transaction.urls
    assert urls is not None
    assert urls.fail is None
    assert urls.ipn is None


def test_transaction_fee_rules_for_odd_values() -> None:
    transaction = _transaction_fixture(rate=1.5, minimal_fee=20.0, permanent_fee="-5")
    assert transaction.rate == "1.5"
    assert transaction.minimal_fee is None
    assert transaction.permanent_fee == -5
    odd = _transaction_fixture(rate=True, minimal_fee="1.5", permanent_fee=False, urls="x")
    assert odd.rate is None
    assert odd.minimal_fee is None
    assert odd.permanent_fee is None
    assert odd.urls is None


def test_missing_fees_and_urls_are_none() -> None:
    transaction = _transaction_fixture()
    assert transaction.rate is None
    assert transaction.minimal_fee is None
    assert transaction.urls is None
