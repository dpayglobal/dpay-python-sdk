from __future__ import annotations

import json

import pytest

from dpay import (
    AccessDeniedError,
    ApiError,
    ApiServerError,
    AuthenticationError,
    CardError,
    DPayClient,
    DPayError,
    DPayValueError,
    InvalidRequestError,
    NotFoundError,
    PaymentRejectedError,
    RateLimitError,
)
from dpay._internal.error_mapper import map_error
from dpay.http.models import ApiResponse
from dpay.testing import MockHttpClient


def _response(status: int, body: str = "{}", headers: dict[str, str] | None = None) -> ApiResponse:
    return ApiResponse(status, headers or {}, body)


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (401, AuthenticationError),
        (403, AccessDeniedError),
        (404, NotFoundError),
        (400, InvalidRequestError),
        (422, InvalidRequestError),
        (500, ApiServerError),
        (503, ApiServerError),
        (418, ApiError),
    ],
)
def test_status_maps_to_exception(status: int, expected: type[ApiError]) -> None:
    assert type(map_error(_response(status))) is expected


def test_every_error_is_a_dpay_error() -> None:
    assert isinstance(map_error(_response(500)), DPayError)


def test_message_prefers_message_over_msg() -> None:
    error = map_error(_response(400, '{"message":"a","msg":"b"}'))
    assert error.message == "a"


def test_message_falls_back_to_msg() -> None:
    assert map_error(_response(400, '{"msg":"b"}')).message == "b"


def test_message_default() -> None:
    assert map_error(_response(400)).message == "Unexpected API error"


def test_error_code_uses_lowercase_key() -> None:
    assert map_error(_response(400, '{"errorcode":"err01"}')).error_code == "err01"
    assert map_error(_response(400, '{"errorCode":"err01"}')).error_code is None


def test_maps_the_code_and_reason_of_cards_and_webhook_errors() -> None:
    body = (
        '{"success":false,"status":"error","code":"WEBHOOK_URL_INVALID","reason":"https_required",'
        '"message":"Invalid webhook URL: https_required"}'
    )
    error = map_error(_response(400, body))

    assert isinstance(error, InvalidRequestError)
    assert error.error_code == "WEBHOOK_URL_INVALID"
    assert error.reason == "https_required"
    assert error.message == "Invalid webhook URL: https_required"


def test_maps_a_missing_checksum_to_an_authentication_error() -> None:
    body = '{"success":false,"status":"error","code":"CHECKSUM_REQUIRED","message":"Missing service or checksum"}'
    error = map_error(_response(401, body))

    assert type(error) is AuthenticationError
    assert error.error_code == "CHECKSUM_REQUIRED"
    assert error.reason is None


def test_code_wins_over_errorcode_and_non_strings_are_ignored() -> None:
    assert map_error(_response(400, '{"code":"A","errorcode":"B"}')).error_code == "A"
    assert map_error(_response(400, '{"code":7,"errorcode":"B"}')).error_code == "B"
    assert map_error(_response(400, '{"reason":["x"]}')).reason is None


def test_rate_limit_has_no_reason() -> None:
    error = map_error(_response(429, '{"code":"X","reason":"y"}'))
    assert isinstance(error, RateLimitError)
    assert error.error_code is None
    assert error.reason is None


def test_field_errors_normalize_400_shape() -> None:
    error = map_error(_response(400, '{"errors":{"value":"jest wymagane"}}'))
    assert error.field_errors == {"value": ["jest wymagane"]}


def test_field_errors_normalize_422_shape() -> None:
    error = map_error(_response(422, '{"errors":{"value":["a","b"]}}'))
    assert error.field_errors == {"value": ["a", "b"]}


def test_field_errors_drop_non_scalar_entries() -> None:
    error = map_error(_response(422, '{"errors":{"value":["a",{"x":1},null]}}'))
    assert error.field_errors == {"value": ["a"]}


def test_field_errors_ignore_non_object() -> None:
    assert map_error(_response(400, '{"errors":"boom"}')).field_errors == {}


def test_raw_body_is_preserved() -> None:
    assert map_error(_response(400, '{"msg":"x"}')).raw_body == '{"msg":"x"}'


def test_invalid_json_still_maps() -> None:
    error = map_error(_response(500, "<html>502</html>"))
    assert isinstance(error, ApiServerError)
    assert error.raw_body == "<html>502</html>"


def test_rate_limit_reads_headers() -> None:
    error = map_error(
        _response(
            429,
            '{"message":"slow down"}',
            {"Retry-After": "30", "X-RateLimit-Limit": "100", "X-RateLimit-Remaining": "0"},
        )
    )
    assert isinstance(error, RateLimitError)
    assert (error.retry_after, error.limit, error.remaining) == (30, 100, 0)


def test_rate_limit_headers_are_case_insensitive() -> None:
    error = map_error(_response(429, "{}", {"retry-after": "5"}))
    assert isinstance(error, RateLimitError)
    assert error.retry_after == 5


def test_rate_limit_survives_garbage_headers() -> None:
    error = map_error(_response(429, "{}", {"Retry-After": "soon"}))
    assert isinstance(error, RateLimitError)
    assert error.retry_after == 0


def test_rate_limit_without_headers() -> None:
    error = map_error(_response(429))
    assert isinstance(error, RateLimitError)
    assert error.retry_after is None


def test_service_raises_mapped_error() -> None:
    from dpay import DPayClient

    transport = MockHttpClient()
    transport.queue_json(404, {"message": "nie ma"})
    client = DPayClient(service="s", secret_hash="h", http_client=transport)

    with pytest.raises(NotFoundError) as error:
        client.payments.details("brak")
    assert error.value.http_status == 404
    assert error.value.message == "nie ma"


def test_rate_limit_reads_the_reset_header() -> None:
    error = map_error(
        _response(
            429,
            '{"message":"Too Many Attempts."}',
            {
                "retry-after": "12",
                "x-ratelimit-limit": "60",
                "x-ratelimit-remaining": "0",
                "x-ratelimit-reset": "1790503560",
            },
        )
    )
    assert isinstance(error, RateLimitError)
    assert (error.retry_after, error.limit, error.remaining, error.reset) == (12, 60, 0, 1790503560)
    assert error.transaction_id is None
    assert error.card_error is None


def test_rate_limit_without_reset_header() -> None:
    error = map_error(_response(429, "{}", {"Retry-After": "30"}))
    assert isinstance(error, RateLimitError)
    assert error.reset is None


def test_register_error_carries_transaction_id_and_card_error() -> None:
    body = (
        '{"status":"failed","message":"Card payment declined","errors":{},'
        '"transactionId":"A75AEBB4-4B89-4834-AD43-EF442C133769",'
        '"cardError":{"code":"payment_declined","declineCode":"51",'
        '"declineMessage":"Insufficient funds or over credit limit"}}'
    )
    error = map_error(_response(400, body))

    assert type(error) is InvalidRequestError
    assert error.transaction_id == "A75AEBB4-4B89-4834-AD43-EF442C133769"
    assert error.card_error is not None
    assert error.card_error.code == "payment_declined"
    assert error.card_error.decline_code == "51"
    assert error.card_error.decline_message == "Insufficient funds or over credit limit"


def test_card_error_keeps_null_fields() -> None:
    body = '{"status":"failed","message":"Declined","cardError":{"code":"payment_declined","declineCode":null,"declineMessage":null}}'
    card_error = map_error(_response(400, body)).card_error

    assert card_error is not None
    assert card_error.code == "payment_declined"
    assert card_error.decline_code is None
    assert card_error.decline_message is None


def test_card_error_accepts_integer_codes() -> None:
    assert CardError.from_api({"code": 5, "declineCode": 51, "declineMessage": True}).decline_code == "51"
    assert CardError.from_api({"code": True}).code is None


def test_errors_without_transaction_context_have_none() -> None:
    error = map_error(_response(400, '{"status":"failed","message":"Invalid checksum","errors":{}}'))
    assert error.transaction_id is None
    assert error.card_error is None


@pytest.mark.parametrize("status", [401, 403, 404, 422, 409, 500], ids=lambda status: f"http-{status}")
def test_every_status_carries_the_transaction_context(status: int) -> None:
    error = map_error(_response(status, '{"transactionId":"tx-1","cardError":{"code":"invalid_card"}}'))
    assert error.transaction_id == "tx-1"
    assert error.card_error is not None
    assert error.card_error.code == "invalid_card"


@pytest.mark.parametrize("transaction_id", ["", 123, None, ["tx"]])
def test_transaction_id_must_be_a_non_empty_string(transaction_id: object) -> None:
    error = map_error(_response(400, json.dumps({"transactionId": transaction_id, "cardError": "x"})))
    assert error.transaction_id is None
    assert error.card_error is None


def test_payment_rejected_transaction_id_lives_on_the_base_class() -> None:
    error = PaymentRejectedError.from_api({"msg": "Rejected", "transactionId": 77})
    assert error.transaction_id == "77"
    assert ApiError("m", 400, transaction_id="tx-1").transaction_id == "tx-1"


def test_extra_request_headers_are_sent_after_the_sdk_headers(
    client: DPayClient, transport: MockHttpClient
) -> None:
    transport.queue_json(200, {"status": "success", "refund": True})
    client.refunds.create("tx-1", message_id="RET-1")

    headers = transport.last_request.headers
    assert list(headers) == ["Accept", "User-Agent", "DigitalPayments-PSP-Message-ID", "Content-Type"]
    assert headers["DigitalPayments-PSP-Message-ID"] == "RET-1"
    assert headers["Accept"] == "application/json"


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("X-Test", "a\r\nX-Other: b"),
        ("X-Test", "a\x00"),
        ("X-Test", "a\x7f"),
        ("X Test", "a"),
        ("X-Test\n", "a"),
    ],
)
def test_header_injection_is_rejected(name: str, value: str) -> None:
    from dpay._internal import base_urls
    from dpay._internal.operation import Operation
    from dpay._internal.requestor import ApiRequestor
    from dpay.config import Config

    transport = MockHttpClient()
    api = ApiRequestor(Config.from_dict({"service": "s", "secret_hash": "h"}), transport)
    operation = Operation("POST", base_urls.PANEL, "/x", lambda response: None, {}, headers={name: value})
    with pytest.raises(DPayValueError, match="Invalid request header"):
        api.execute(operation)
    assert transport.requests == []
