from __future__ import annotations

from typing import Any

from dpay._internal import base_urls
from dpay._internal.checksum import ChecksumCalculator
from dpay._internal.error_mapper import map_error
from dpay._internal.operation import Operation, decode_dict_or_fail
from dpay.http.models import ApiResponse
from dpay.payout.models import PayoutDetails

_FAILURE_STATUSES = ("error", "failed")


def details(
    service: str, checksum: ChecksumCalculator, withdraw_id: int, timestamp: int | None = None
) -> Operation:
    body: dict[str, Any] = {"service": service}
    if timestamp is not None:
        body["timestamp"] = timestamp
    body["withdraw_id"] = withdraw_id
    body["checksum"] = checksum.ordered_body(body)
    return Operation(
        "POST",
        base_urls.PANEL,
        "/api/v1/pbl/withdraws/details",
        _parse_details,
        body,
    )


def _parse_details(response: ApiResponse) -> PayoutDetails:
    data = decode_dict_or_fail(response)
    status = data.get("status")
    if isinstance(status, str) and status.lower() in _FAILURE_STATUSES and "id" not in data:
        raise map_error(response)
    return PayoutDetails.from_api(data)
