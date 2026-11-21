from __future__ import annotations

from typing import Any

from dpay._internal.php import is_scalar, php_int, php_strval
from dpay.exceptions import (
    AccessDeniedError,
    ApiError,
    ApiServerError,
    AuthenticationError,
    InvalidRequestError,
    NotFoundError,
    RateLimitError,
)
from dpay.http.models import ApiResponse


def map_error(response: ApiResponse) -> ApiError:
    # Imported here: the dpay.card package imports the requestor, which imports this module
    from dpay.card.card_error import CardError

    status = response.status
    raw_body = response.body
    decoded = response.decode_json()
    data: dict[str, Any] = decoded if isinstance(decoded, dict) else {}

    message = "Unexpected API error"
    if isinstance(data.get("message"), str):
        message = data["message"]
    elif isinstance(data.get("msg"), str):
        message = data["msg"]

    # Cards API and webhook errors carry ``code`` (e.g. CHECKSUM_REQUIRED, WEBHOOK_URL_INVALID)
    error_code: str | None = None
    if isinstance(data.get("code"), str):
        error_code = data["code"]
    elif isinstance(data.get("errorcode"), str):
        error_code = data["errorcode"]
    reason = data["reason"] if isinstance(data.get("reason"), str) else None
    field_errors = _normalize_field_errors(data.get("errors"))
    # Payments API: the transaction created before the error and the card decline (declined saved-card charge)
    raw_transaction_id = data.get("transactionId")
    transaction_id = (
        raw_transaction_id if isinstance(raw_transaction_id, str) and raw_transaction_id else None
    )
    raw_card_error = data.get("cardError")
    card_error = CardError.from_api(raw_card_error) if isinstance(raw_card_error, dict) else None

    if status == 429:
        return RateLimitError(
            message,
            status,
            _int_header(response, "Retry-After"),
            _int_header(response, "X-RateLimit-Limit"),
            _int_header(response, "X-RateLimit-Remaining"),
            raw_body,
            _int_header(response, "X-RateLimit-Reset"),
        )
    arguments = (message, status, error_code, field_errors, raw_body, reason, transaction_id, card_error)
    if status == 401:
        return AuthenticationError(*arguments)
    if status == 403:
        return AccessDeniedError(*arguments)
    if status == 404:
        return NotFoundError(*arguments)
    if status in (400, 422):
        return InvalidRequestError(*arguments)
    if status >= 500:
        return ApiServerError(*arguments)
    return ApiError(*arguments)


def _normalize_field_errors(errors: Any) -> dict[str, list[str]]:
    if isinstance(errors, list):
        items: list[tuple[Any, Any]] = list(enumerate(errors))
    elif isinstance(errors, dict):
        items = list(errors.items())
    else:
        return {}
    normalized: dict[str, list[str]] = {}
    for field, messages in items:
        if isinstance(messages, str):
            normalized[php_strval(field)] = [messages]
        elif isinstance(messages, list):
            normalized[php_strval(field)] = [
                php_strval(message) for message in messages if is_scalar(message)
            ]
    return normalized


def _int_header(response: ApiResponse, name: str) -> int | None:
    value = response.get_header(name)
    return None if value is None else php_int(value)
