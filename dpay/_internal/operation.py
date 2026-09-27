from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from dpay.exceptions import ApiServerError
from dpay.http.models import ApiResponse


@dataclass(frozen=True)
class Operation:
    method: str
    host: str
    path: str
    parse: Callable[[ApiResponse], Any]
    body: dict[str, Any] | None = None
    raise_for_status: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


def decode_json_or_fail(response: ApiResponse) -> Any:
    data = response.decode_json()
    if data is None:
        raise ApiServerError("Invalid JSON in API response", response.status, None, {}, response.body)
    return data


def decode_dict_or_fail(response: ApiResponse) -> dict[str, Any]:
    data = decode_json_or_fail(response)
    return data if isinstance(data, dict) else {}


def decode_list_or_fail(response: ApiResponse) -> list[Any]:
    data = decode_json_or_fail(response)
    return data if isinstance(data, list) else []


def decode_envelope_or_fail(response: ApiResponse) -> dict[str, Any]:
    """The ``data`` object of a ``{"status": "success", "data": {...}}`` envelope, ``{}`` when missing."""
    inner = decode_dict_or_fail(response).get("data")
    return inner if isinstance(inner, dict) else {}
