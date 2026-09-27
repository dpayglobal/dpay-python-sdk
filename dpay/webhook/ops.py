from __future__ import annotations

import re
import time
from collections.abc import Sequence
from typing import Any

from dpay._internal import base_urls
from dpay._internal.checksum import ChecksumCalculator
from dpay._internal.operation import Operation, decode_dict_or_fail
from dpay._internal.php import is_php_int
from dpay.exceptions import DPayValueError
from dpay.webhook.event import EventPage
from dpay.webhook.event_type import WebhookEventType

_EVENT_ID = re.compile(r"evt_[0-9a-z]{26}")


def list_events(
    service: str,
    checksum: ChecksumCalculator,
    *,
    types: Sequence[str] | None,
    created_from: str | None,
    created_to: str | None,
    starting_after: str | None,
    limit: int | None,
    timestamp: int | None,
) -> Operation:
    signed_at = int(time.time()) if timestamp is None else timestamp
    body: dict[str, Any] = {"service": service, "timestamp": signed_at}
    if types is not None:
        if isinstance(types, str) or len(types) == 0 or len(set(types)) != len(types):
            raise DPayValueError("Event types must be a non-empty list of distinct types")
        WebhookEventType.assert_allowed(types, WebhookEventType.MERCHANT, "the Events API")
        body["types"] = list(types)
    if created_from is not None:
        body["created_from"] = created_from
    if created_to is not None:
        body["created_to"] = created_to
    if starting_after is not None:
        if not isinstance(starting_after, str) or _EVENT_ID.fullmatch(starting_after) is None:
            raise DPayValueError("starting_after must be an event id (evt_...)")
        body["starting_after"] = starting_after
    if limit is not None:
        if not is_php_int(limit) or limit < 1 or limit > 100:
            raise DPayValueError("limit must be between 1 and 100")
        body["limit"] = limit
    # sha256(service|hash|timestamp) - the filters stay out of the checksum
    body["checksum"] = checksum.secret_second(service, [str(signed_at)])
    return Operation(
        "POST",
        base_urls.API_PAYMENTS,
        "/api/v1_0/events",
        lambda response: EventPage.from_api(decode_dict_or_fail(response)),
        body,
    )
