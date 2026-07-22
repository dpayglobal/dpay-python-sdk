from __future__ import annotations

import pytest

from dpay import (
    ApiError,
    DPayClient,
    InvalidRequestError,
    NotFoundError,
    RateLimitError,
)
from dpay.testing import MockHttpClient


def test_unknown_withdraw_envelope_is_not_parsed_as_a_waiting_payout(
    client: DPayClient, transport: MockHttpClient
) -> None:
    transport.queue_json(200, {"status": "error", "message": "Withdraw does not exist"})
    with pytest.raises(ApiError) as error:
        client.payouts.details(999999)
    assert error.value.message == "Withdraw does not exist"


def test_unknown_withdraw_with_error_status_code(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(404, {"status": "error", "message": "Withdraw does not exist"})
    with pytest.raises(NotFoundError):
        client.payouts.details(999999)


def test_failed_status_marker_is_also_rejected(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, {"status": "failed", "message": "Unknown route"})
    with pytest.raises(ApiError):
        client.payouts.details(1)


def test_valid_payout_carrying_a_status_field_still_parses(
    client: DPayClient, transport: MockHttpClient
) -> None:
    transport.queue_json(200, {"id": 7, "state": 1, "status": "error", "net": 10.0})
    details = client.payouts.details(7)
    assert details.id == 7
    assert details.is_processed


def test_empty_payout_body_keeps_php_behaviour(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, {})
    details = client.payouts.details(1)
    assert details.id == 0
    assert details.is_waiting


@pytest.mark.parametrize(
    "errors",
    [{"service": ["Nieznany serwis"]}, {"service": "Nieznany serwis"}],
)
def test_unknown_service_on_details(
    client: DPayClient, transport: MockHttpClient, errors: dict[str, object]
) -> None:
    transport.queue_json(422, {"message": "The given data was invalid.", "errors": errors})
    with pytest.raises(InvalidRequestError) as error:
        client.payments.details("tx-1")
    assert error.value.http_status == 422
    assert error.value.field_errors == {"service": ["Nieznany serwis"]}


def test_unknown_service_on_refund(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(422, {"errors": {"service": ["Nieznany serwis"]}})
    with pytest.raises(InvalidRequestError):
        client.refunds.create("tx-1")


def test_unknown_service_on_check_availability_is_an_error_not_an_outcome(
    client: DPayClient, transport: MockHttpClient
) -> None:
    transport.queue_json(422, {"errors": {"service": ["Nieznany serwis"]}})
    with pytest.raises(InvalidRequestError):
        client.refunds.check_availability("tx-1")


def test_missing_transaction_message_is_surfaced(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(404, {"message": "transaction does not exist", "0": "transaction does not exist"})
    with pytest.raises(NotFoundError) as error:
        client.payments.details("brak")
    assert error.value.message == "transaction does not exist"


def test_legacy_numeric_key_only_body_still_maps(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(404, {"0": "transaction does not exist"})
    with pytest.raises(NotFoundError) as error:
        client.payments.details("brak")
    assert error.value.message == "Unexpected API error"


def test_foreign_transaction_is_a_not_found(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(404, {"message": "transaction does not exist"})
    with pytest.raises(NotFoundError):
        client.payments.details("cudza-transakcja")


def test_missing_transaction_on_check_availability_is_not_a_business_outcome(
    client: DPayClient, transport: MockHttpClient
) -> None:
    transport.queue_json(
        404,
        {
            "status": "error",
            "refund": False,
            "message": "Transaction does not exist!",
            "0": "Transaction does not exist!",
        },
    )
    with pytest.raises(NotFoundError) as error:
        client.refunds.check_availability("nie-istnieje")
    assert error.value.message == "Transaction does not exist!"


def test_foreign_transaction_on_check_availability_is_not_a_business_outcome(
    client: DPayClient, transport: MockHttpClient
) -> None:
    transport.queue_json(404, {"refund": False, "message": "Transaction does not exist!"})
    with pytest.raises(NotFoundError):
        client.refunds.check_availability("cudza-transakcja")


def test_business_refusal_codes_still_return_an_outcome(
    client: DPayClient, transport: MockHttpClient
) -> None:
    transport.queue_json(402, {"refund": False, "message": "Transakcja nie została opłacona"})
    availability = client.refunds.check_availability("tx-1")
    assert availability.is_available is False
    assert availability.http_status == 402


def test_unknown_withdraw_404_surfaces_the_handler_message(
    client: DPayClient, transport: MockHttpClient
) -> None:
    transport.queue_json(404, {"status": "error", "message": "Withdraw does not exist!"})
    with pytest.raises(NotFoundError) as error:
        client.payouts.details(999999)
    assert error.value.message == "Withdraw does not exist!"


def test_rate_limit_envelope_exposes_message(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(
        429,
        {"status": "error", "message": "Too many requests", "error": "rate_limit"},
        {"Retry-After": "12"},
    )
    with pytest.raises(RateLimitError) as error:
        client.payments.details("tx-1")
    assert error.value.message == "Too many requests"
    assert error.value.retry_after == 12
    assert '"error":"rate_limit"' in error.value.raw_body
