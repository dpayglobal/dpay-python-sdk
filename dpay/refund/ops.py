from __future__ import annotations

from typing import Any

from dpay._internal import base_urls
from dpay._internal.checksum import ChecksumCalculator
from dpay._internal.error_mapper import map_error
from dpay._internal.operation import Operation, decode_dict_or_fail
from dpay.http.models import ApiResponse
from dpay.money import Money
from dpay.refund.models import Refund, RefundAvailability

_AVAILABILITY_OUTCOMES = (200, 400, 402, 406, 409, 410, 411)


def _signed_body(
    service: str,
    checksum: ChecksumCalculator,
    transaction_id: str,
    amount: Money | None,
    reason: str | None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"service": service, "transaction_id": transaction_id}
    if amount is not None:
        body["value"] = amount.to_decimal()
    if reason is not None:
        body["reason"] = reason
    body["checksum"] = checksum.ordered_body(list(body.values()))
    return body


def create(
    service: str,
    checksum: ChecksumCalculator,
    transaction_id: str,
    amount: Money | None,
    reason: str | None,
) -> Operation:
    return Operation(
        "POST",
        base_urls.PANEL,
        "/api/v1/pbl/refund",
        lambda response: Refund.from_api(decode_dict_or_fail(response)),
        _signed_body(service, checksum, transaction_id, amount, reason),
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
    if status in _AVAILABILITY_OUTCOMES:
        return True
    return status == 401 and data.get("message") != "Unauthorized request"
