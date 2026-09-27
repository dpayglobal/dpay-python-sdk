"""Webhook targets, event types, the Events API and event envelopes (SDK 0.2.0)."""

from __future__ import annotations

import re
from typing import Any

import pytest

from dpay import (
    DPayClient,
    DPayValueError,
    EventPage,
    Money,
    RegisterPaymentRequest,
    ReturnUrls,
    TransactionType,
    WebhookEvent,
    WebhookEventType,
    WebhookTarget,
)
from dpay.testing import MockHttpClient
from tests import api_vectors

EVENT_ID = "evt_01k6a8q2m4pz7h8c3v5n9t2x6y"
OTHER_EVENT_ID = "evt_01k6a8q2m4pz7h8c3v5n9t2x6a"


@pytest.fixture
def vectors_client(transport: MockHttpClient) -> DPayClient:
    return DPayClient(service=api_vectors.SERVICE, secret_hash=api_vectors.SECRET_HASH, http_client=transport)


def _event(event_id: str, event_type: str = "payment.succeeded") -> dict[str, Any]:
    return {
        "id": event_id,
        "type": event_type,
        "api_version": "2026-10-01",
        "created": "2026-09-27T10:05:00Z",
        "livemode": True,
        "service": "sdk-test-service",
        "data": {"object": {"object": "payment", "id": "TX-1"}},
    }


# WebhookEventType


def test_event_type_groups() -> None:
    assert len(WebhookEventType.MERCHANT) == 11
    assert len(WebhookEventType.PAYMENT_REGISTRATION) == 9
    assert WebhookEventType.REFUND == ("refund.succeeded", "refund.failed")
    assert WebhookEventType.CAPTURE == ("payment.captured",)
    assert WebhookEventType.WEBHOOK_TEST not in WebhookEventType.MERCHANT
    assert set(WebhookEventType.PAYMENT_REGISTRATION) <= set(WebhookEventType.MERCHANT)
    assert WebhookEventType.PAYOUT_PAID not in WebhookEventType.PAYMENT_REGISTRATION


def test_assert_allowed_names_the_context() -> None:
    message = 'Event "payout.paid" is not allowed in the webhook object of a refund'
    with pytest.raises(DPayValueError, match=re.escape(message)):
        WebhookEventType.assert_allowed(["refund.failed", "payout.paid"], WebhookEventType.REFUND, "a refund")


# WebhookTarget


def test_target_sends_the_url_first_and_events_only_when_given() -> None:
    assert WebhookTarget.create("https://shop.example/webhooks").to_api() == {
        "url": "https://shop.example/webhooks"
    }
    target = WebhookTarget.create("HTTPS://shop.example/webhooks", ["refund.failed", "refund.succeeded"])
    assert list(target.to_api()) == ["url", "events"]
    assert target.to_api()["events"] == ["refund.failed", "refund.succeeded"]


@pytest.mark.parametrize(
    "url",
    [
        "http://shop.example/webhooks",
        "shop.example/webhooks",
        "https://",
        "",
        "ftp://shop.example",
        "https://a b.pl",
    ],
)
def test_target_requires_a_valid_https_url(url: str) -> None:
    with pytest.raises(DPayValueError, match="must be a valid https:// URL"):
        WebhookTarget.create(url)


def test_target_url_is_at_most_500_bytes() -> None:
    base = "https://shop.example/"
    WebhookTarget.create(base + "x" * (500 - len(base)))
    with pytest.raises(DPayValueError, match="at most 500 characters"):
        WebhookTarget.create(base + "x" * (501 - len(base)))


def test_target_events_are_distinct_merchant_events() -> None:
    with pytest.raises(DPayValueError, match="must be distinct"):
        WebhookTarget.create("https://shop.example/webhooks", ["refund.failed", "refund.failed"])
    with pytest.raises(DPayValueError, match=re.escape('Event "webhook.test" is not allowed')):
        WebhookTarget.create("https://shop.example/webhooks", ["webhook.test"])
    with pytest.raises(DPayValueError, match="list of event types"):
        WebhookTarget.create("https://shop.example/webhooks", "refund.failed")


def test_payment_registration_accepts_only_payment_events() -> None:
    request = RegisterPaymentRequest.create(
        Money.pln(1000), TransactionType.TRANSFERS, ReturnUrls("https://a.pl/ok", "https://a.pl/fail")
    )
    with pytest.raises(DPayValueError, match="webhook object of a payment registration"):
        request.with_webhook(WebhookTarget.create("https://shop.example/webhooks", ["payout.paid"]))
    request.with_webhook(
        WebhookTarget.create("https://shop.example/webhooks", list(WebhookEventType.PAYMENT_REGISTRATION))
    )


# Refund and capture with a webhook target


def test_refund_webhook_values_are_hashed_in_the_order_sent(
    vectors_client: DPayClient, transport: MockHttpClient
) -> None:
    transport.queue_json(
        200, {"status": "success", "refund": True, "message": f"dpay.pl {api_vectors.TRANSACTION_ID}"}
    )

    refund = vectors_client.refunds.create(
        api_vectors.TRANSACTION_ID,
        Money.pln(1500),
        "Zwrot",
        WebhookTarget.create("https://shop.example/webhooks/refunds", ["refund.succeeded", "refund.failed"]),
    )

    body = transport.last_request_body
    assert list(body) == ["service", "transaction_id", "value", "reason", "webhook", "checksum"]
    assert body["value"] == "15.00"
    # ...|15.00|Zwrot|https://shop.example/webhooks/refunds|refund.succeeded|refund.failed|hash
    expected = api_vectors.vector(api_vectors.ORDERED_BODY, "refund_with_reason_and_webhook")
    assert body["checksum"] == expected["checksum"]
    assert refund.is_accepted


def test_refund_webhook_accepts_only_refund_events(client: DPayClient) -> None:
    with pytest.raises(DPayValueError, match="webhook object of a refund"):
        client.refunds.create(
            "TX", None, None, WebhookTarget.create("https://shop.example/webhooks", ["payment.succeeded"])
        )


def test_capture_webhook_stays_out_of_the_checksum(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, {"success": True, "message": {"redirectType": "SUCCESS"}})
    transport.queue_json(200, {"success": True, "message": {"redirectType": "SUCCESS"}})

    client.cards.capture("tx-1", Money.pln(1500))
    without = transport.last_request_body
    client.cards.capture("tx-1", Money.pln(1500), WebhookTarget.create("https://shop.test/webhooks/captures"))
    with_webhook = transport.last_request_body

    assert list(with_webhook) == ["service", "amount", "webhook", "checksum"]
    assert with_webhook["webhook"] == {"url": "https://shop.test/webhooks/captures"}
    assert with_webhook["checksum"] == without["checksum"]


def test_capture_webhook_accepts_only_payment_captured(client: DPayClient) -> None:
    target = WebhookTarget.create("https://shop.example/webhooks", ["payment.succeeded"])
    with pytest.raises(DPayValueError, match="webhook object of a card capture"):
        client.cards.capture("tx-1", Money.pln(100), target)


# Events API


def test_list_signs_the_timestamp_and_sends_filters(
    vectors_client: DPayClient, transport: MockHttpClient
) -> None:
    transport.queue_json(
        200, {"status": "success", "data": [_event(EVENT_ID)], "has_more": False, "next_starting_after": None}
    )

    page = vectors_client.events.list(
        types=["payment.succeeded", "refund.failed"], limit=50, timestamp=1790503500
    )

    assert transport.last_request.url == "https://api-payments.dpay.pl/api/v1_0/events"
    assert transport.last_request_body == {
        "service": "sdk-test-service",
        "timestamp": 1790503500,
        "types": ["payment.succeeded", "refund.failed"],
        "limit": 50,
        # sha256(service|hash|timestamp) - filters stay out of the checksum
        "checksum": api_vectors.vector(api_vectors.SECRET_SECOND, "events_list")["checksum"],
    }
    assert isinstance(page, EventPage)
    assert len(page.data) == 1
    assert page.data[0].type == "payment.succeeded"
    assert page.has_more is False
    assert page.next_starting_after is None


def test_list_keeps_the_body_order_of_every_filter(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, {"status": "success", "data": []})
    client.events.list(
        limit=1,
        starting_after=EVENT_ID,
        created_to="2026-09-30T00:00:00Z",
        created_from="2026-09-01T00:00:00Z",
        types=["payout.paid"],
        timestamp=1790503500,
    )
    assert list(transport.last_request_body) == [
        "service",
        "timestamp",
        "types",
        "created_from",
        "created_to",
        "starting_after",
        "limit",
        "checksum",
    ]


def test_list_defaults_the_timestamp_to_now(client: DPayClient, transport: MockHttpClient) -> None:
    import time

    transport.queue_json(200, {"status": "success", "data": []})
    before = int(time.time())
    client.events.list()
    body = transport.last_request_body
    assert list(body) == ["service", "timestamp", "checksum"]
    assert before <= body["timestamp"] <= int(time.time())


def test_iterate_pages_until_the_end(vectors_client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(
        200,
        {"status": "success", "data": [_event(EVENT_ID)], "has_more": True, "next_starting_after": EVENT_ID},
    )
    transport.queue_json(
        200,
        {
            "status": "success",
            "data": [_event(OTHER_EVENT_ID)],
            "has_more": False,
            "next_starting_after": OTHER_EVENT_ID,
        },
    )

    ids = [event.id for event in vectors_client.events.iterate(limit=1)]

    assert ids == [EVENT_ID, OTHER_EVENT_ID]
    assert len(transport.requests) == 2
    assert transport.last_request_body["starting_after"] == EVENT_ID
    assert transport.last_request_body["limit"] == 1


def test_iterate_stops_without_a_cursor(client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, {"status": "success", "data": [_event(EVENT_ID)], "has_more": True})
    assert [event.id for event in client.events.iterate()] == [EVENT_ID]
    assert len(transport.requests) == 1


@pytest.mark.parametrize(
    ("filters", "message"),
    [
        ({"types": ["merchant.updated"]}, 'Event "merchant.updated" is not allowed'),
        ({"types": ["webhook.test"]}, 'Event "webhook.test" is not allowed'),
        ({"types": []}, "non-empty list of distinct types"),
        ({"types": ["payout.paid", "payout.paid"]}, "non-empty list of distinct types"),
        ({"types": "payout.paid"}, "non-empty list of distinct types"),
        ({"starting_after": "evt_123"}, "starting_after must be an event id"),
        ({"starting_after": EVENT_ID.upper()}, "starting_after must be an event id"),
        ({"limit": 0}, "limit must be between 1 and 100"),
        ({"limit": 101}, "limit must be between 1 and 100"),
    ],
)
def test_rejects_invalid_filters_before_calling_the_api(
    client: DPayClient, transport: MockHttpClient, filters: dict[str, Any], message: str
) -> None:
    with pytest.raises(DPayValueError, match=message):
        client.events.list(**filters)
    assert transport.requests == []


# Event envelopes


def test_event_exposes_the_envelope() -> None:
    event = WebhookEvent.from_api(
        {
            **_event(EVENT_ID, "recurring_payment.canceled"),
            "livemode": False,
            "service": None,
            "merchant_ref": "m-7",
        }
    )
    assert event.id == EVENT_ID
    assert event.type == "recurring_payment.canceled"
    assert event.api_version == "2026-10-01"
    assert event.created == "2026-09-27T10:05:00Z"
    assert event.is_livemode is False
    assert event.service is None
    assert event.merchant_ref == "m-7"
    assert event.object_type == "payment"
    assert event.object == {"object": "payment", "id": "TX-1"}


@pytest.mark.parametrize("livemode", [True, None, 0, "false"])
def test_only_an_explicit_false_is_test_mode(livemode: Any) -> None:
    assert WebhookEvent.from_api({"livemode": livemode}).is_livemode is True
    assert WebhookEvent.from_api({}).is_livemode is True


def test_malformed_envelope_falls_back_to_empty_values() -> None:
    event = WebhookEvent.from_api({"id": 5, "type": ["x"], "data": {"object": "nope"}})
    assert event.id == ""
    assert event.type == ""
    assert event.object == {}
    assert event.object_type is None
    assert WebhookEvent.from_api({"data": [1]}).object == {}


def test_event_page_skips_malformed_items() -> None:
    page = EventPage.from_api(
        {"data": [_event(EVENT_ID), "junk", 5], "has_more": "yes", "next_starting_after": 7}
    )
    assert [event.id for event in page.data] == [EVENT_ID]
    assert page.has_more is False
    assert page.next_starting_after is None
    assert EventPage.from_api({"data": "nope"}).data == []
