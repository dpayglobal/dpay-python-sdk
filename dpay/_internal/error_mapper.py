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
    status = response.status
    raw_body = response.body
    decoded = response.decode_json()
    data: dict[str, Any] = decoded if isinstance(decoded, dict) else {}

    message = "Unexpected API error"
    if isinstance(data.get("message"), str):
        message = data["message"]
    elif isinstance(data.get("msg"), str):
        message = data["msg"]

    error_code = data["errorcode"] if isinstance(data.get("errorcode"), str) else None
    field_errors = _normalize_field_errors(data.get("errors"))

    if status == 429:
        return RateLimitError(
            message,
            status,
            _int_header(response, "Retry-After"),
            _int_header(response, "X-RateLimit-Limit"),
            _int_header(response, "X-RateLimit-Remaining"),
            raw_body,
        )
    if status == 401:
        return AuthenticationError(message, status, error_code, field_errors, raw_body)
    if status == 403:
        return AccessDeniedError(message, status, error_code, field_errors, raw_body)
    if status == 404:
        return NotFoundError(message, status, error_code, field_errors, raw_body)
    if status in (400, 422):
        return InvalidRequestError(message, status, error_code, field_errors, raw_body)
    if status >= 500:
        return ApiServerError(message, status, error_code, field_errors, raw_body)
    return ApiError(message, status, error_code, field_errors, raw_body)


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
