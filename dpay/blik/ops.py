from __future__ import annotations

from typing import Any

from dpay._internal import base_urls
from dpay._internal.checksum import ChecksumCalculator
from dpay._internal.operation import Operation, decode_dict_or_fail, decode_envelope_or_fail
from dpay.blik.enums import BlikAliasType
from dpay.blik.models import BlikAlias
from dpay.http.models import ApiResponse


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
        lambda response: BlikAlias.from_api(decode_envelope_or_fail(response)),
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
