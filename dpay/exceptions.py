from __future__ import annotations

from typing import Any

from dpay._internal.php import is_scalar, php_json_encode, php_strval


class DPayError(Exception):
    pass


class DPayValueError(DPayError, ValueError):
    pass


class TransportError(DPayError):
    pass


class SignatureVerificationError(DPayError):
    pass


class CardEncryptionError(DPayError):
    pass


class ApiError(DPayError):
    def __init__(
        self,
        message: str,
        http_status: int,
        error_code: str | None = None,
        field_errors: dict[str, list[str]] | None = None,
        raw_body: str = "",
    ) -> None:
        super().__init__(message)
        self.message = message
        self.http_status = http_status
        self.error_code = error_code
        self.field_errors: dict[str, list[str]] = field_errors or {}
        self.raw_body = raw_body


class AuthenticationError(ApiError):
    pass


class InvalidRequestError(ApiError):
    pass


class AccessDeniedError(ApiError):
    pass


class NotFoundError(ApiError):
    pass


class ApiServerError(ApiError):
    pass


class RateLimitError(ApiError):
    def __init__(
        self,
        message: str,
        http_status: int,
        retry_after: int | None = None,
        limit: int | None = None,
        remaining: int | None = None,
        raw_body: str = "",
    ) -> None:
        super().__init__(message, http_status, None, {}, raw_body)
        self.retry_after = retry_after
        self.limit = limit
        self.remaining = remaining


class PaymentRejectedError(ApiError):
    def __init__(
        self,
        message: str,
        http_status: int,
        error_code: str | None = None,
        field_errors: dict[str, list[str]] | None = None,
        raw_body: str = "",
        transaction_id: str | None = None,
    ) -> None:
        super().__init__(message, http_status, error_code, field_errors, raw_body)
        self.transaction_id = transaction_id

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> PaymentRejectedError:
        raw_message = data.get("msg")
        message = raw_message if isinstance(raw_message, str) else "Payment rejected"
        additional = data.get("additionalInfo")
        additional = additional if isinstance(additional, dict) else {}
        raw_code = additional.get("error")
        error_code = raw_code if isinstance(raw_code, str) else None
        transaction_id = data.get("transactionId")
        return cls(
            message,
            200,
            error_code,
            {},
            php_json_encode(data),
            php_strval(transaction_id) if is_scalar(transaction_id) else None,
        )


class CardPaymentError(ApiError):
    @classmethod
    def from_api(cls, data: dict[str, Any]) -> CardPaymentError:
        raw_message = data.get("message")
        message = raw_message if isinstance(raw_message, str) else "Card payment failed"
        return cls(message, 200, message, {}, php_json_encode(data))
