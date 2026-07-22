from __future__ import annotations

from typing import Any

from dpay._internal import base_urls
from dpay._internal.checksum import ChecksumCalculator
from dpay._internal.operation import Operation, decode_dict_or_fail
from dpay.blik.enums import BlikAliasType
from dpay.blik.models import BlikAlias, BlikRecurringStatus
from dpay.http.models import ApiResponse


def _envelope(response: ApiResponse) -> dict[str, Any]:
    data = decode_dict_or_fail(response)
    inner = data.get("data")
    return inner if isinstance(inner, dict) else {}


def alias(service: str, checksum: ChecksumCalculator, alias_value: str, alias_type: str) -> Operation:
    BlikAliasType.assert_valid(alias_type)
    body: dict[str, Any] = {
        "service": service,
        "alias_value": alias_value,
        "alias_type": alias_type,
    }
    body["checksum"] = checksum.secret_second(service, [alias_value])
    return Operation(
        "POST",
        base_urls.API_PAYMENTS,
        "/api/v1_0/payments/blik/aliases",
        lambda response: BlikAlias.from_api(_envelope(response)),
        body,
    )


def unregister_alias(
    service: str,
    checksum: ChecksumCalculator,
    alias_value: str,
    alias_type: str,
    reason: str | None,
) -> Operation:
    BlikAliasType.assert_valid(alias_type)
    body: dict[str, Any] = {
        "service": service,
        "alias_value": alias_value,
        "alias_type": alias_type,
    }
    if reason is not None:
        body["reason"] = reason
    body["checksum"] = checksum.secret_second(service, [alias_value])
    return Operation(
        "POST",
        base_urls.API_PAYMENTS,
        "/api/v1_0/payments/blik/aliases/unregister",
        _discard,
        body,
    )


def _discard(response: ApiResponse) -> None:
    decode_dict_or_fail(response)
    return None


def recurring_status(service: str, checksum: ChecksumCalculator, alias_value: str) -> Operation:
    body: dict[str, Any] = {"service": service, "alias_value": alias_value}
    body["checksum"] = checksum.secret_second(service, [alias_value])
    return Operation(
        "POST",
        base_urls.API_PAYMENTS,
        "/api/v1_0/payments/blik/recurring/status",
        lambda response: BlikRecurringStatus.from_api(_envelope(response)),
        body,
    )
