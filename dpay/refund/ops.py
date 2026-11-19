from __future__ import annotations

import re
from typing import Any

from dpay._internal import base_urls
from dpay._internal.checksum import ChecksumCalculator
from dpay._internal.error_mapper import map_error
from dpay._internal.operation import Operation, decode_dict_or_fail
from dpay.exceptions import DPayValueError
from dpay.http.models import ApiResponse
from dpay.money import Money
from dpay.refund.models import Refund, RefundAvailability
from dpay.webhook.event_type import WebhookEventType
from dpay.webhook.target import WebhookTarget

# Request header with your own refund identifier; it sets the refund transfer title.
MESSAGE_ID_HEADER = "DigitalPayments-PSP-Message-ID"
_MESSAGE_ID = re.compile(r"[\x20-\x7e]+")


def _signed_body(
    service: str,
    checksum: ChecksumCalculator,
    transaction_id: str,
    amount: Money | None,
    reason: str | None,
    webhook: WebhookTarget | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"service": service, "transaction_id": transaction_id}
    if amount is not None:
        body["value"] = amount.to_decimal()
    if reason is not None:
        body["reason"] = reason
    if webhook is not None:
        body["webhook"] = webhook.to_api()
    # Values of the whole body in the order sent, the webhook object flattened (url, events...)
    body["checksum"] = checksum.ordered_body(body)
    return body


def create(
    service: str,
    checksum: ChecksumCalculator,
    transaction_id: str,
    amount: Money | None,
    reason: str | None,
    webhook: WebhookTarget | None = None,
    message_id: str | None = None,
) -> Operation:
    if webhook is not None:
        webhook.assert_events_allowed(WebhookEventType.REFUND, "a refund")
    headers: dict[str, str] = {}
    if message_id is not None:
        if (
            not isinstance(message_id, str)
            or _MESSAGE_ID.fullmatch(message_id) is None
            or message_id.strip(" ") == ""
        ):
            raise DPayValueError("Refund message ID must be non-empty printable ASCII")
        # Header only - not in the body and not in the checksum
        headers[MESSAGE_ID_HEADER] = message_id
    return Operation(
        "POST",
        base_urls.PANEL,
        "/api/v1/pbl/refund",
        lambda response: Refund.from_api(decode_dict_or_fail(response)),
        _signed_body(service, checksum, transaction_id, amount, reason, webhook),
        headers=headers,
    )


def check_availability(
    service: str,
    checksum: ChecksumCalculator,
    transaction_id: str,
    amount: Money | None,
    reason: str | None,
) -> Operation:
    return Operation(
        "POST",
        base_urls.PANEL,
        "/api/v1/pbl/check-refund-availability",
        _parse_availability,
        _signed_body(service, checksum, transaction_id, amount, reason),
        raise_for_status=False,
    )


def _parse_availability(response: ApiResponse) -> RefundAvailability:
    data = response.decode_json()
    if isinstance(data, dict) and "refund" in data and _is_outcome(response.status, data):
        return RefundAvailability.from_api(data, response.status)
    raise map_error(response)


def _is_outcome(status: int, data: dict[str, Any]) -> bool:
    # 200 and every 4xx business refusal (400, 402, 404, 406, 409, 410, 411, 423...) carrying ``refund``;
    # a 401 only when it is not the checksum error
    if status == 401:
        return data.get("message") != "Unauthorized request"
    return status == 200 or 400 <= status < 500
