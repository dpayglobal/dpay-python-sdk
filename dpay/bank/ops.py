from __future__ import annotations

import time

from dpay._internal import base_urls
from dpay._internal.checksum import ChecksumCalculator
from dpay._internal.operation import Operation, decode_json_or_fail
from dpay._internal.server_trim import required, sign_panel_body
from dpay.bank.models import Bank
from dpay.http.models import ApiResponse


def all_banks() -> Operation:
    return Operation("GET", base_urls.PANEL, "/api/v1/pbl/banks", _parse_banks)


def for_service(service: str, checksum: ChecksumCalculator, timestamp: int | None = None) -> Operation:
    body = sign_panel_body(
        checksum,
        {
            "service": required(service, "service"),
            "timestamp": int(time.time()) if timestamp is None else timestamp,
        },
    )
    return Operation("POST", base_urls.PANEL, "/api/v1/pbl/banks", _parse_banks, body)


def _parse_banks(response: ApiResponse) -> list[Bank]:
    data = decode_json_or_fail(response)
    items = list(data.values()) if isinstance(data, dict) else data
    return [Bank.from_api(item) for item in items if isinstance(item, dict)]
