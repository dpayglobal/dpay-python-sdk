"""Payout list, iteration and full payout details (SDK 0.3.0)."""

from __future__ import annotations

import hashlib
from typing import Any

import pytest

from dpay import (
    DPayClient,
    DPayValueError,
    Money,
    NotFoundError,
    PayoutState,
    PayoutType,
)
from dpay.aio import AsyncDPayClient
from dpay.testing import MockAsyncHttpClient, MockHttpClient

EMPTY_PAGE: dict[str, Any] = {
    "withdraws": [],
    "meta": {"page": 1, "per_page": 50, "total": 0, "total_pages": 0},
}


def _shop_client(transport: MockHttpClient) -> DPayClient:
    return DPayClient(service="MyShop", secret_hash="secret123", http_client=transport)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _row(withdraw_id: int) -> dict[str, Any]:
    return {
        "id": withdraw_id,
        "type": "direct",
        "state": 0,
        "net": "1.00",
        "fee": "0.00",
        "gross": "1.00",
        "currency_code": "PLN",
        "declined": 0,
    }


def test_payout_enums() -> None:
    assert PayoutState.ALL == (0, 1, -1)
    assert (PayoutState.WAITING, PayoutState.PROCESSED, PayoutState.FAILED) == (0, 1, -1)
    assert PayoutType.ALL == ("standard", "direct", "paysafecard")


def test_details_of_a_regular_payout_is_paysafecard_aware(transport: MockHttpClient) -> None:
    transport.queue_json(
        200,
        {
            "id": 12346,
            "state": 0,
            "net": 5.0,
            "fee": 0.5,
            "gross": 5.5,
            "creation_date": "2026-07-01 10:00:00",
            "direct_settlement": 0,
            "paysafecard": 1,
            "nrb": "PL61109010140000071219812874",
            "declined": 0,
        },
    )
    details = _shop_client(transport).payouts.details(12346)

    assert details.is_paysafecard
    assert details.is_waiting
    assert details.currency == "PLN"
    assert details.export_date is None
    assert details.net == Money.pln(500)


def test_list_sends_filters_in_checksum_order(transport: MockHttpClient) -> None:
    transport.queue_json(
        200,
        {
            "withdraws": [
                {
                    "id": 12345,
                    "type": "standard",
                    "state": 1,
                    "net": "27.15",
                    "fee": "3.06",
                    "gross": "30.21",
                    "currency_code": "EUR",
                    "creation_date": "2026-08-01 10:00:00",
                    "export_date": "2026-08-01 14:20:00",
                    "declined": 0,
                }
            ],
            "meta": {"page": 2, "per_page": 10, "total": 11, "total_pages": 2},
        },
    )
    page = _shop_client(transport).payouts.list(
        {
            "type": PayoutType.STANDARD,
            "state": PayoutState.PROCESSED,
            "date_to": "2026-08-31 23:59:59",
            "date_from": "2026-08-01",
        },
        2,
        10,
    )

    assert transport.last_request.url == "https://panel.dpay.pl/api/v1/pbl/withdraws"
    body = transport.last_request_body
    assert list(body) == ["service", "date_from", "date_to", "state", "type", "page", "per_page", "checksum"]
    assert body["state"] == 1
    assert body["checksum"] == _sha("MyShop|2026-08-01|2026-08-31 23:59:59|1|standard|2|10|secret123")
    assert body["checksum"] == "5be864bc1b81a002fe134dbaed5db1d6517db76fdc952842b756da253ceb504b"

    assert len(page.items) == 1
    item = page.items[0]
    assert item.id == 12345
    assert item.type == PayoutType.STANDARD
    assert item.is_processed
    assert not item.is_declined
    assert item.net == Money.of(2715, "EUR")
    assert item.fee == Money.of(306, "EUR")
    assert item.gross == Money.of(3021, "EUR")
    assert item.currency == "EUR"
    assert item.export_date == "2026-08-01 14:20:00"
    assert page.meta.page == 2
    assert page.meta.total == 11
    assert not page.has_more


def test_minimal_list_signs_service_only(transport: MockHttpClient) -> None:
    transport.queue_json(200, EMPTY_PAGE)
    page = _shop_client(transport).payouts.list()

    body = transport.last_request_body
    assert list(body) == ["service", "checksum"]
    assert body["checksum"] == _sha("MyShop|secret123")
    assert page.items == []
    assert not page.has_more


def test_failed_and_waiting_state_filters_are_signed(transport: MockHttpClient) -> None:
    client = _shop_client(transport)
    transport.queue_json(200, EMPTY_PAGE)
    client.payouts.list({"state": PayoutState.FAILED})
    assert transport.last_request_body["checksum"] == _sha("MyShop|-1|secret123")

    # state 0 is a value, not a missing filter
    transport.queue_json(200, EMPTY_PAGE)
    client.payouts.list({"state": PayoutState.WAITING})
    assert transport.last_request_body["state"] == 0
    assert transport.last_request_body["checksum"] == _sha("MyShop|0|secret123")


def test_none_filters_are_not_sent(transport: MockHttpClient) -> None:
    transport.queue_json(200, EMPTY_PAGE)
    _shop_client(transport).payouts.list({"state": None, "date_from": None})
    assert list(transport.last_request_body) == ["service", "checksum"]


def test_date_filters_are_sent_trimmed_because_the_api_trims_before_the_checksum(
    transport: MockHttpClient,
) -> None:
    transport.queue_json(200, EMPTY_PAGE)
    _shop_client(transport).payouts.list({"date_from": " 2026-08-01\n", "date_to": "2026-08-31 23:59:59 "})

    body = transport.last_request_body
    assert body["date_from"] == "2026-08-01"
    assert body["date_to"] == "2026-08-31 23:59:59"
    assert body["checksum"] == _sha("MyShop|2026-08-01|2026-08-31 23:59:59|secret123")


def test_iterate_walks_all_pages(transport: MockHttpClient) -> None:
    transport.queue_json(
        200,
        {"withdraws": [_row(3), _row(2)], "meta": {"page": 1, "per_page": 2, "total": 3, "total_pages": 2}},
    )
    transport.queue_json(
        200, {"withdraws": [_row(1)], "meta": {"page": 2, "per_page": 2, "total": 3, "total_pages": 2}}
    )

    ids = [item.id for item in _shop_client(transport).payouts.iterate({"type": PayoutType.DIRECT}, 2)]

    assert ids == [3, 2, 1]
    assert len(transport.requests) == 2
    assert transport.last_request_body["page"] == 2
    assert transport.last_request_body["per_page"] == 2


def test_iterate_stops_on_an_empty_page(transport: MockHttpClient) -> None:
    transport.queue_json(
        200, {"withdraws": [], "meta": {"page": 1, "per_page": 2, "total": 5, "total_pages": 3}}
    )
    assert list(_shop_client(transport).payouts.iterate()) == []
    assert transport.last_request_body["page"] == 1


@pytest.mark.parametrize(
    ("filters", "page", "per_page", "message"),
    [
        ({"state": 2}, None, None, 'Invalid payout state "2"'),
        ({"state": "1"}, None, None, 'Invalid payout state "1"'),
        ({"state": True}, None, None, 'Invalid payout state "True"'),
        ({"type": "instant"}, None, None, 'Invalid payout type "instant"'),
        ({"date_from": " "}, None, None, "date_from must not be empty"),
        ({"date_to": "\t\n"}, None, None, "date_to must not be empty"),
        ({"date_from": 20260801}, None, None, "date_from must be a string"),
        ({}, 0, None, "page must be at least 1"),
        ({}, None, 201, "per_page must be between 1 and 200"),
        ({}, None, 0, "per_page must be between 1 and 200"),
    ],
    ids=[
        "state",
        "state-string",
        "state-bool",
        "type",
        "empty-date",
        "blank-date",
        "date-not-string",
        "page-0",
        "per-page-201",
        "per-page-0",
    ],
)
def test_list_validation(
    transport: MockHttpClient, filters: dict[str, Any], page: int | None, per_page: int | None, message: str
) -> None:
    with pytest.raises(DPayValueError, match=f"^{message}$"):
        _shop_client(transport).payouts.list(filters, page, per_page)
    assert transport.requests == []


def test_list_rejects_unknown_filters(transport: MockHttpClient) -> None:
    with pytest.raises(DPayValueError, match=r'^Unknown payout filter "status"$'):
        _shop_client(transport).payouts.list({"status": 1})
    with pytest.raises(DPayValueError, match=r'^Unknown payout filter "status", "limit"$'):
        _shop_client(transport).payouts.list({"state": 1, "status": 1, "limit": 2})


def test_details_full(transport: MockHttpClient) -> None:
    transport.queue_json(
        200,
        {
            "settlement": {
                "id": 12345,
                "state": 1,
                "net": "27.15",
                "fee": "3.06",
                "gross": "30.21",
                "currency_code": "PLN",
                "creation_date": "2026-08-01 10:00:00",
                "export_date": "2026-08-01 14:20:00",
                "direct_settlement": 0,
                "declined": 0,
                "paysafecard": 0,
                "nrb": "PL61109010140000071219812874",
            },
            "summary": {"net": "27.15", "fee": "3.06", "gross": "30.21", "count": 3},
            "transactions": [
                {
                    "payment_id": "8F2C1A90-5B7E-4C31-9A02-7D6E4B1F3C88",
                    "date": "2026-07-31 12:04:11",
                    "net": "9.05",
                    "fee": "1.02",
                    "gross": "10.07",
                    "service_id": 42,
                    "service_name": "Sklep testowy",
                    "custom": "order-1234",
                    "ipksef": None,
                }
            ],
            "meta": {"page": 1, "per_page": 1, "total": 3, "total_pages": 3},
        },
    )
    settlement = _shop_client(transport).payouts.details_full(12345, 1, 1)

    assert transport.last_request.url == "https://panel.dpay.pl/api/v1/pbl/withdraws/details/full"
    body = transport.last_request_body
    assert list(body) == ["service", "withdraw_id", "page", "per_page", "checksum"]
    assert body["checksum"] == _sha("MyShop|12345|1|1|secret123")

    header = settlement.settlement
    assert header.id == 12345
    assert header.is_processed
    assert not header.is_paysafecard
    assert header.export_date == "2026-08-01 14:20:00"
    assert header.nrb == "PL61109010140000071219812874"
    assert settlement.summary_net.minor == 2715
    assert settlement.summary_fee.minor == 306
    assert settlement.summary_gross.minor == 3021
    assert settlement.summary_count == 3
    assert len(settlement.positions) == 1
    position = settlement.positions[0]
    assert position.payment_id == "8F2C1A90-5B7E-4C31-9A02-7D6E4B1F3C88"
    assert position.date == "2026-07-31 12:04:11"
    assert (position.net.minor, position.fee.minor, position.gross.minor) == (905, 102, 1007)
    assert position.service_id == 42
    assert position.service_name == "Sklep testowy"
    assert position.custom == "order-1234"
    assert position.ipksef is None
    assert settlement.meta.has_more


def test_details_full_in_foreign_currency_and_minimal_body(transport: MockHttpClient) -> None:
    transport.queue_json(
        200,
        {
            "settlement": {
                "id": 7,
                "state": 0,
                "net": "10.00",
                "fee": "0.00",
                "gross": "10.00",
                "currency_code": "EUR",
                "direct_settlement": 1,
                "declined": 0,
                "receiver": {
                    "nrb": "PL61109010140000071219812874",
                    "title": "FV 1",
                    "receiverName": "Firma",
                    "receiverAddress": "Lisboa",
                    "amount": "10.00",
                },
            },
            "summary": {"net": "10.00", "fee": "0.00", "gross": "10.00", "count": 1},
            "transactions": [
                {"payment_id": "P-1", "date": None, "net": "10.00", "fee": "0.00", "gross": "10.00"}
            ],
            "meta": {"page": 1, "per_page": 100, "total": 1, "total_pages": 1},
        },
    )
    settlement = _shop_client(transport).payouts.details_full(7)

    assert list(transport.last_request_body) == ["service", "withdraw_id", "checksum"]
    assert transport.last_request_body["checksum"] == _sha("MyShop|7|secret123")
    assert settlement.settlement.currency == "EUR"
    assert settlement.summary_net.currency == "EUR"
    assert settlement.positions[0].net.currency == "EUR"
    assert settlement.positions[0].service_id is None
    receiver = settlement.settlement.receiver
    assert receiver is not None
    assert receiver.receiver_name == "Firma"
    assert receiver.amount == Money.of(1000, "EUR")
    assert not settlement.meta.has_more


def test_details_full_validates_paging_and_maps_not_found(transport: MockHttpClient) -> None:
    client = _shop_client(transport)
    with pytest.raises(DPayValueError, match=r"^per_page must be between 1 and 500$"):
        client.payouts.details_full(1, None, 501)
    with pytest.raises(DPayValueError, match=r"^page must be at least 1$"):
        client.payouts.details_full(1, 0)

    transport.queue_json(404, {"status": "error", "message": "Withdraw does not exist!"})
    with pytest.raises(NotFoundError, match="Withdraw does not exist!"):
        client.payouts.details_full(999)


def test_details_full_of_an_empty_answer_has_safe_defaults(transport: MockHttpClient) -> None:
    transport.queue_json(200, {})
    settlement = _shop_client(transport).payouts.details_full(1)
    assert settlement.settlement.id == 0
    assert settlement.summary_count == 0
    assert settlement.summary_net == Money.pln(0)
    assert settlement.positions == []
    assert settlement.meta.page == 1
    assert not settlement.meta.has_more


async def test_async_list_iterate_and_details_full(
    async_client: AsyncDPayClient,
    async_transport: MockAsyncHttpClient,
    client: DPayClient,
    transport: MockHttpClient,
) -> None:
    for queue in (async_transport, transport):
        queue.queue_json(
            200, {"withdraws": [_row(2)], "meta": {"page": 1, "per_page": 1, "total": 2, "total_pages": 2}}
        )
        queue.queue_json(
            200, {"withdraws": [_row(1)], "meta": {"page": 2, "per_page": 1, "total": 2, "total_pages": 2}}
        )
        queue.queue_json(200, {"settlement": {"id": 9}, "meta": {}})

    ids = [item.id async for item in async_client.payouts.iterate({"state": 0}, 1)]
    settlement = await async_client.payouts.details_full(9, 2, 50)
    sync_ids = [item.id for item in client.payouts.iterate({"state": 0}, 1)]
    client.payouts.details_full(9, 2, 50)

    assert ids == sync_ids == [2, 1]
    assert settlement.settlement.id == 9
    assert [request.body for request in async_transport.requests] == [
        request.body for request in transport.requests
    ]

    async_transport.queue_json(200, EMPTY_PAGE)
    page = await async_client.payouts.list()
    assert page.items == []
