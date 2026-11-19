from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from dpay._internal import base_urls
from dpay._internal.checksum import ChecksumCalculator
from dpay._internal.error_mapper import map_error
from dpay._internal.operation import Operation, decode_dict_or_fail
from dpay._internal.php import is_php_int
from dpay._internal.server_trim import required, sign_panel_body
from dpay.exceptions import DPayValueError
from dpay.http.models import ApiResponse
from dpay.payout.enums import PayoutState, PayoutType
from dpay.payout.models import PayoutDetails, PayoutPage, PayoutSettlement

_FAILURE_STATUSES = ("error", "failed")
_LIST_FILTERS = ("date_from", "date_to", "state", "type")


def details(
    service: str, checksum: ChecksumCalculator, withdraw_id: int, timestamp: int | None = None
) -> Operation:
    body: dict[str, Any] = {"service": required(service, "service")}
    if timestamp is not None:
        body["timestamp"] = timestamp
    body["withdraw_id"] = withdraw_id
    return Operation(
        "POST",
        base_urls.PANEL,
        "/api/v1/pbl/withdraws/details",
        _parse_details,
        sign_panel_body(checksum, body),
    )


def _parse_details(response: ApiResponse) -> PayoutDetails:
    data = decode_dict_or_fail(response)
    status = data.get("status")
    if isinstance(status, str) and status.lower() in _FAILURE_STATUSES and "id" not in data:
        raise map_error(response)
    return PayoutDetails.from_api(data)


def list_payouts(
    service: str,
    checksum: ChecksumCalculator,
    filters: Mapping[str, Any] | None,
    page: int | None,
    per_page: int | None,
) -> Operation:
    # Fixed order, independent of the order of the filters - the checksum follows the body
    body: dict[str, Any] = {"service": required(service, "service")}
    body.update(_list_filters(filters or {}))
    _add_page(body, page, per_page, 200)
    return Operation(
        "POST",
        base_urls.PANEL,
        "/api/v1/pbl/withdraws",
        lambda response: PayoutPage.from_api(decode_dict_or_fail(response)),
        sign_panel_body(checksum, body),
    )


def details_full(
    service: str,
    checksum: ChecksumCalculator,
    withdraw_id: int,
    page: int | None,
    per_page: int | None,
) -> Operation:
    body: dict[str, Any] = {"service": required(service, "service"), "withdraw_id": withdraw_id}
    _add_page(body, page, per_page, 500)
    return Operation(
        "POST",
        base_urls.PANEL,
        "/api/v1/pbl/withdraws/details/full",
        lambda response: PayoutSettlement.from_api(decode_dict_or_fail(response)),
        sign_panel_body(checksum, body),
    )


def _list_filters(filters: Mapping[str, Any]) -> dict[str, Any]:
    """Validates the payout list filters - any mapping; wrong keys, types and values raise DPayValueError -
    and returns them as body fields in the order the checksum signs them."""
    unknown = [key for key in filters if key not in _LIST_FILTERS]
    if unknown:
        raise DPayValueError('Unknown payout filter "{}"'.format('", "'.join(str(key) for key in unknown)))
    body: dict[str, Any] = {}
    for field in ("date_from", "date_to"):
        value = filters.get(field)
        if value is None:
            continue
        if not isinstance(value, str):
            raise DPayValueError(f"{field} must be a string")
        # The API trims strings before it verifies the checksum - an untrimmed value would fail with 401
        body[field] = required(value, field)
    state = filters.get("state")
    if state is not None:
        # bool is an int subclass in Python - not an integer here
        if not is_php_int(state):
            raise DPayValueError("state must be an integer")
        PayoutState.assert_valid(state)
        body["state"] = state
    payout_type = filters.get("type")
    if payout_type is not None:
        if not isinstance(payout_type, str):
            raise DPayValueError("type must be a string")
        PayoutType.assert_valid(payout_type)
        body["type"] = payout_type
    return body


def _add_page(body: dict[str, Any], page: int | None, per_page: int | None, max_per_page: int) -> None:
    if page is not None:
        if not is_php_int(page) or page < 1:
            raise DPayValueError("page must be at least 1")
        body["page"] = page
    if per_page is not None:
        if not is_php_int(per_page) or per_page < 1 or per_page > max_per_page:
            raise DPayValueError(f"per_page must be between 1 and {max_per_page}")
        body["per_page"] = per_page
