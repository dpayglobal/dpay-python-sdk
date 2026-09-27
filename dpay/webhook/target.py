from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from dpay._internal.validation import byte_length, is_valid_url
from dpay.exceptions import DPayValueError
from dpay.webhook.event_type import WebhookEventType


class WebhookTarget:
    """Per-request webhook address - the ``webhook`` object of a payment registration, refund or capture.

    Events of that payment go to this URL, signed with the service's webhook secret, on top of the
    endpoints configured in the panel. An empty ``events`` list means every event the request allows.
    """

    def __init__(self, url: str, events: Sequence[str] = ()) -> None:
        if byte_length(url) > 500:
            raise DPayValueError("Webhook URL must be at most 500 characters")
        if not is_valid_url(url) or url[:8].lower() != "https://":
            raise DPayValueError(f'Webhook URL "{url}" must be a valid https:// URL')
        if isinstance(events, str):
            raise DPayValueError("Webhook events must be a list of event types")
        if len(set(events)) != len(events):
            raise DPayValueError("Webhook events must be distinct")
        WebhookEventType.assert_allowed(events, WebhookEventType.MERCHANT, "a request")
        self.url = url
        self.events: list[str] = list(events)

    @classmethod
    def create(cls, url: str, events: Sequence[str] = ()) -> WebhookTarget:
        return cls(url, events)

    def assert_events_allowed(self, allowed: Iterable[str], context: str) -> None:
        WebhookEventType.assert_allowed(self.events, allowed, context)

    def to_api(self) -> dict[str, Any]:
        # ``url`` first, then ``events`` - the refund checksum hashes the values in this order
        data: dict[str, Any] = {"url": self.url}
        if self.events:
            data["events"] = list(self.events)
        return data
