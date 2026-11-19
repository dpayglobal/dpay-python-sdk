"""Panel API (``/api/v1/pbl/*``) strings are sent and signed trimmed the way the API trims them (Laravel 13
``TrimStrings``, ``Str::trim()``), sync and async."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import Any

import pytest

from dpay import DPayClient, DPayValueError, Money, WebhookTarget
from dpay._internal.server_trim import CODE_POINTS, required, server_trim, trim_strings
from dpay.aio import AsyncDPayClient
from dpay.testing import MockAsyncHttpClient, MockHttpClient

TX = "30D9493D-1D73-3FBD-A5D4-633723CC7A68"
EMPTY_PAGE: dict[str, Any] = {
    "withdraws": [],
    "meta": {"page": 1, "per_page": 50, "total": 0, "total_pages": 0},
}
REFUND_OK = {"status": "success", "refund": True, "message": "ok"}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _client(transport: MockHttpClient, service: str = "MyShop") -> DPayClient:
    return DPayClient(service=service, secret_hash="secret123", http_client=transport)


def test_the_set_is_the_65_code_points_of_laravel_str_trim() -> None:
    assert len(CODE_POINTS) == 65
    assert {0x0000, 0x0085, 0x00A0, 0x00AD, 0x180E, 0x200B, 0x3000, 0xFEFF, 0x1D159, 0xE0020} <= CODE_POINTS
    # Python's str.strip() is a different set: U+001C-U+001F are stripped by it, not by the API
    assert not {0x1C, 0x1D, 0x1E, 0x1F} & CODE_POINTS
    assert server_trim("\x1cx\x1f") == "\x1cx\x1f"
    for code_point in CODE_POINTS:
        assert server_trim(f"{chr(code_point)}a{chr(code_point)}b{chr(code_point)}") == f"a{chr(code_point)}b"


def test_trim_strings_keeps_keys_order_and_other_types() -> None:
    body = {
        "b": " x ",
        "a": 1,
        "n": None,
        "f": False,
        "w": {"url": "\u200bhttps://a.pl\n", "events": [" e "]},
    }
    assert trim_strings(body) == {
        "b": "x",
        "a": 1,
        "n": None,
        "f": False,
        "w": {"url": "https://a.pl", "events": ["e"]},
    }
    assert list(trim_strings(body)) == ["b", "a", "n", "f", "w"]


def test_required_rejects_blank_values() -> None:
    assert required("\u00a0x\n", "field") == "x"
    with pytest.raises(DPayValueError, match=r"^field must not be empty$"):
        required("\u3000 \ufeff", "field")
    with pytest.raises(DPayValueError, match=r"^field must be a string$"):
        required(5, "field")  # type: ignore[arg-type]


def test_refund_sends_and_signs_trimmed_values() -> None:
    transport = MockHttpClient()
    transport.queue_json(200, REFUND_OK)

    _client(transport, " MyShop ").refunds.create(f" {TX}\n", Money.pln(1500), "\u3000reklamacja\u200b")

    body = transport.last_request_body
    assert body == {
        "service": "MyShop",
        "transaction_id": TX,
        "value": "15.00",
        "reason": "reklamacja",
        "checksum": "5c00684addf39fda89d3d6cff88abf26bb8173119056fd3012050422943c798a",
    }
    assert body["checksum"] == _sha(f"MyShop|{TX}|15.00|reklamacja|secret123")


def test_refund_webhook_url_is_trimmed() -> None:
    transport = MockHttpClient()
    transport.queue_json(200, REFUND_OK)
    webhook = WebhookTarget.create("https://shop.example/webhooks/refunds", ["refund.succeeded"])
    webhook.url = "https://shop.example/webhooks/refunds\u200b"

    _client(transport).refunds.create(TX, None, None, webhook)

    body = transport.last_request_body
    assert body["webhook"]["url"] == "https://shop.example/webhooks/refunds"
    assert body["checksum"] == _sha(
        f"MyShop|{TX}|https://shop.example/webhooks/refunds|refund.succeeded|secret123"
    )


def test_reason_blank_after_trimming_is_sent_empty_and_hashed_as_an_empty_segment() -> None:
    transport = MockHttpClient()
    transport.queue_json(200, {"status": "success", "refund": True, "message": "Refund available"})

    _client(transport).refunds.check_availability(TX, Money.pln(1500), "\ufeff \n")

    body = transport.last_request_body
    assert list(body) == ["service", "transaction_id", "value", "reason", "checksum"]
    assert body["reason"] == ""
    assert body["checksum"] == "12dcb016aa2302bbe8ea71be9007eeacdedaeab1d4dc317966bab1b1e8d53a1c"
    assert body["checksum"] == _sha(f"MyShop|{TX}|15.00||secret123")


@pytest.mark.parametrize(
    "call",
    [
        lambda client: client.refunds.create(" \t"),
        lambda client: client.refunds.create("\u00a0\t"),
        lambda client: client.refunds.check_availability(""),
        lambda client: client.payments.details("\u200b"),
    ],
    ids=["create", "create-unicode", "availability-empty", "details"],
)
def test_blank_transaction_id_is_rejected_before_the_request(call: Callable[[DPayClient], object]) -> None:
    transport = MockHttpClient()
    with pytest.raises(DPayValueError, match=r"^transaction_id must not be empty$"):
        call(_client(transport))
    assert transport.requests == []


def test_refund_validation_order() -> None:
    transport = MockHttpClient()
    client = _client(transport, "\u3000")
    with pytest.raises(DPayValueError, match=r"^Refund message ID must be non-empty printable ASCII$"):
        client.refunds.create(" ", message_id="RET\n")
    with pytest.raises(DPayValueError, match=r"^service must not be empty$"):
        client.refunds.create(" ", message_id="RET-1")
    with pytest.raises(DPayValueError, match=r"^transaction_id must not be empty$"):
        _client(transport).refunds.create(" ", message_id="RET-1")
    assert transport.requests == []


def test_message_id_header_is_not_trimmed() -> None:
    transport = MockHttpClient()
    transport.queue_json(200, REFUND_OK)
    _client(transport).refunds.create(TX, message_id=" RET-1 ")
    assert transport.last_request.headers["DigitalPayments-PSP-Message-ID"] == " RET-1 "
    assert transport.last_request_body["checksum"] == _sha(f"MyShop|{TX}|secret123")


def test_details_transaction_id_is_trimmed() -> None:
    transport = MockHttpClient()
    transport.queue_json(200, {"transaction": {"id": TX, "status": "paid"}})

    _client(transport).payments.details(f"\t{TX} ")

    body = transport.last_request_body
    assert body["transaction_id"] == TX
    assert body["checksum"] == "3b345f55900ae6a43220dd14a3827ed9a26a02a3eb46b856d302e2baa44b48a4"


def test_banks_for_service_trims_the_configured_service() -> None:
    transport = MockHttpClient()
    transport.queue_json(200, [])

    client = _client(transport, " MyShop\ufeff")
    client.banks.for_service(1753100000)

    body = transport.last_request_body
    assert body["service"] == "MyShop"
    assert body["checksum"] == "189d0301f163fb105c9f3d607e8fe0adbbfc5ecd8e16271a682d672f43ab623c"
    # The configuration keeps the value, the payments API still gets it untrimmed
    assert client.config.service == " MyShop\ufeff"


@pytest.mark.parametrize(
    "call",
    [
        lambda client: client.banks.for_service(1753100000),
        lambda client: client.payments.details(TX),
        lambda client: client.refunds.check_availability(TX),
        lambda client: client.payouts.details(1),
        lambda client: client.payouts.list({"unknown": 1}),
        lambda client: client.payouts.details_full(1),
    ],
    ids=["banks", "details", "availability", "payout-details", "payout-list", "payout-details-full"],
)
def test_blank_service_is_rejected_on_panel_calls(call: Callable[[DPayClient], object]) -> None:
    transport = MockHttpClient()
    with pytest.raises(DPayValueError, match=r"^service must not be empty$"):
        call(_client(transport, "\u3000"))
    assert transport.requests == []


def test_payouts_trim_service_and_date_filters() -> None:
    transport = MockHttpClient()
    for _ in range(3):
        transport.queue_json(200, EMPTY_PAGE)
    client = _client(transport, "MyShop\n")

    client.payouts.list({"date_from": "\ufeff2026-08-01 ", "date_to": "\u30002026-08-31 23:59:59\u200b"})
    body = transport.last_request_body
    assert body["service"] == "MyShop"
    assert body["date_from"] == "2026-08-01"
    assert body["date_to"] == "2026-08-31 23:59:59"
    assert body["checksum"] == "59828763de9628f5794f01750e9876aba13876caac856f62daf7840552f28d6f"

    client.payouts.details(7, 1753100000)
    assert transport.last_request_body["service"] == "MyShop"
    assert transport.last_request_body["checksum"] == _sha("MyShop|1753100000|7|secret123")

    client.payouts.details_full(7, 2)
    assert transport.last_request_body["service"] == "MyShop"
    assert transport.last_request_body["checksum"] == _sha("MyShop|7|2|secret123")

    with pytest.raises(DPayValueError, match=r"^date_from must not be empty$"):
        client.payouts.list({"date_from": " \n"})


def test_payments_api_requests_are_not_trimmed() -> None:
    transport = MockHttpClient()
    transport.queue_json(200, {"status": "success", "data": {"status": "ACTIVE"}})
    _client(transport, " MyShop ").recurring.status("SUB-1")
    assert transport.last_request_body["service"] == " MyShop "


async def test_async_client_trims_like_the_sync_client() -> None:
    sync_transport = MockHttpClient()
    async_transport = MockAsyncHttpClient()
    for transport in (sync_transport, async_transport):
        transport.queue_json(200, REFUND_OK)
        transport.queue_json(200, {"refund": True})
        transport.queue_json(200, {"transaction": {"id": TX}})
        transport.queue_json(200, [])
        transport.queue_json(200, EMPTY_PAGE)
        transport.queue_json(200, {"id": 7})
        transport.queue_json(200, {"settlement": {}, "summary": {}, "transactions": [], "meta": {}})

    sync_client = _client(sync_transport, " MyShop ")
    sync_client.refunds.create(f" {TX}\n", Money.pln(1500), "\u3000reklamacja\u200b")
    sync_client.refunds.check_availability(f"{TX}\u00a0", None, " ")
    sync_client.payments.details(f"\t{TX}")
    sync_client.banks.for_service(1753100000)
    sync_client.payouts.list({"date_from": "\ufeff2026-08-01 "})
    sync_client.payouts.details(7)
    sync_client.payouts.details_full(7)

    async_client = AsyncDPayClient(service=" MyShop ", secret_hash="secret123", http_client=async_transport)
    await async_client.refunds.create(f" {TX}\n", Money.pln(1500), "\u3000reklamacja\u200b")
    await async_client.refunds.check_availability(f"{TX}\u00a0", None, " ")
    await async_client.payments.details(f"\t{TX}")
    await async_client.banks.for_service(1753100000)
    await async_client.payouts.list({"date_from": "\ufeff2026-08-01 "})
    await async_client.payouts.details(7)
    await async_client.payouts.details_full(7)

    assert [request.body for request in async_transport.requests] == [
        request.body for request in sync_transport.requests
    ]
    assert async_transport.requests[0].body is not None
    assert '"transaction_id":"30D9493D-1D73-3FBD-A5D4-633723CC7A68"' in async_transport.requests[0].body
    assert all('"service":"MyShop"' in str(request.body) for request in async_transport.requests)

    with pytest.raises(DPayValueError, match=r"^transaction_id must not be empty$"):
        await async_client.payments.details(" ")
    with pytest.raises(DPayValueError, match=r"^state must be an integer$"):
        await async_client.payouts.list({"state": True})
