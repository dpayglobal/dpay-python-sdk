from __future__ import annotations

import pytest

from dpay import (
    AccessDeniedError,
    ApiError,
    ApiServerError,
    AuthenticationError,
    DPayError,
    InvalidRequestError,
    NotFoundError,
    RateLimitError,
)
from dpay._internal.error_mapper import map_error
from dpay.http.models import ApiResponse
from dpay.testing import MockHttpClient


def _response(status: int, body: str = "{}", headers: dict[str, str] | None = None) -> ApiResponse:
    return ApiResponse(status, headers or {}, body)


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (401, AuthenticationError),
        (403, AccessDeniedError),
        (404, NotFoundError),
        (400, InvalidRequestError),
        (422, InvalidRequestError),
        (500, ApiServerError),
        (503, ApiServerError),
        (418, ApiError),
    ],
)
def test_status_maps_to_exception(status: int, expected: type[ApiError]) -> None:
    assert type(map_error(_response(status))) is expected


def test_every_error_is_a_dpay_error() -> None:
    assert isinstance(map_error(_response(500)), DPayError)


def test_message_prefers_message_over_msg() -> None:
    error = map_error(_response(400, '{"message":"a","msg":"b"}'))
    assert error.message == "a"


def test_message_falls_back_to_msg() -> None:
    assert map_error(_response(400, '{"msg":"b"}')).message == "b"


def test_message_default() -> None:
    assert map_error(_response(400)).message == "Unexpected API error"


def test_error_code_uses_lowercase_key() -> None:
    assert map_error(_response(400, '{"errorcode":"err01"}')).error_code == "err01"
    assert map_error(_response(400, '{"errorCode":"err01"}')).error_code is None


def test_field_errors_normalize_400_shape() -> None:
    error = map_error(_response(400, '{"errors":{"value":"jest wymagane"}}'))
    assert error.field_errors == {"value": ["jest wymagane"]}


def test_field_errors_normalize_422_shape() -> None:
    error = map_error(_response(422, '{"errors":{"value":["a","b"]}}'))
    assert error.field_errors == {"value": ["a", "b"]}


def test_field_errors_drop_non_scalar_entries() -> None:
    error = map_error(_response(422, '{"errors":{"value":["a",{"x":1},null]}}'))
    assert error.field_errors == {"value": ["a"]}


def test_field_errors_ignore_non_object() -> None:
    assert map_error(_response(400, '{"errors":"boom"}')).field_errors == {}


def test_raw_body_is_preserved() -> None:
    assert map_error(_response(400, '{"msg":"x"}')).raw_body == '{"msg":"x"}'


def test_invalid_json_still_maps() -> None:
    error = map_error(_response(500, "<html>502</html>"))
    assert isinstance(error, ApiServerError)
    assert error.raw_body == "<html>502</html>"


def test_rate_limit_reads_headers() -> None:
    error = map_error(
        _response(
            429,
            '{"message":"slow down"}',
            {"Retry-After": "30", "X-RateLimit-Limit": "100", "X-RateLimit-Remaining": "0"},
        )
    )
    assert isinstance(error, RateLimitError)
    assert (error.retry_after, error.limit, error.remaining) == (30, 100, 0)


def test_rate_limit_headers_are_case_insensitive() -> None:
    error = map_error(_response(429, "{}", {"retry-after": "5"}))
    assert isinstance(error, RateLimitError)
    assert error.retry_after == 5


def test_rate_limit_survives_garbage_headers() -> None:
    error = map_error(_response(429, "{}", {"Retry-After": "soon"}))
    assert isinstance(error, RateLimitError)
    assert error.retry_after == 0


def test_rate_limit_without_headers() -> None:
    error = map_error(_response(429))
    assert isinstance(error, RateLimitError)
    assert error.retry_after is None


def test_service_raises_mapped_error() -> None:
    from dpay import DPayClient

    transport = MockHttpClient()
    transport.queue_json(404, {"message": "nie ma"})
    client = DPayClient(service="s", secret_hash="h", http_client=transport)

    with pytest.raises(NotFoundError) as error:
        client.payments.details("brak")
    assert error.value.http_status == 404
    assert error.value.message == "nie ma"
