from __future__ import annotations

from typing import Any

from dpay._internal import base_urls
from dpay._internal.checksum import ChecksumCalculator
from dpay._internal.operation import Operation, decode_envelope_or_fail
from dpay.http.models import ApiResponse
from dpay.recurring.models import RecurringRetryResult, RecurringStatus


def status(service: str, checksum: ChecksumCalculator, alias: str) -> Operation:
    body: dict[str, Any] = {
        "service": service,
        "alias": alias,
        "checksum": checksum.secret_second(service, [alias]),
    }
    return Operation(
        "POST",
        base_urls.API_PAYMENTS,
        "/api/v1_0/payments/recurring/status",
        lambda response: RecurringStatus.from_api(decode_envelope_or_fail(response)),
        body,
    )


def retry(service: str, checksum: ChecksumCalculator, transaction_id: str) -> Operation:
    body: dict[str, Any] = {
        "service": service,
        "transaction_id": transaction_id,
        "checksum": checksum.secret_second(service, [transaction_id]),
    }
    return Operation(
        "POST",
        base_urls.API_PAYMENTS,
        "/api/v1_0/payments/recurring/retry",
        lambda response: RecurringRetryResult.from_api(decode_envelope_or_fail(response)),
        body,
    )


def cancel(service: str, checksum: ChecksumCalculator, alias: str, reason: str | None) -> Operation:
    body: dict[str, Any] = {"service": service, "alias": alias}
    if reason is not None:
        body["reason"] = reason
    # sha256(service|hash|alias|cancel) - the operation name keeps a status checksum from cancelling
    body["checksum"] = checksum.secret_second(service, [alias, "cancel"])
    return Operation(
        "POST",
        base_urls.API_PAYMENTS,
        "/api/v1_0/payments/recurring/cancel",
        _parse_cancel,
        body,
    )


def _parse_cancel(response: ApiResponse) -> str:
    status = decode_envelope_or_fail(response).get("status")
    return status if isinstance(status, str) else RecurringStatus.UNREGISTERED
