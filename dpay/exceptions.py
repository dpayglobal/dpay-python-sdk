from __future__ import annotations

from typing import TYPE_CHECKING, Any

from dpay._internal.php import is_scalar, php_json_encode, php_strval

if TYPE_CHECKING:
    from dpay.card.card_error import CardError


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
        reason: str | None = None,
        transaction_id: str | None = None,
        card_error: CardError | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.http_status = http_status
        self.error_code = error_code
        self.field_errors: dict[str, list[str]] = field_errors or {}
        self.raw_body = raw_body
        # Detailed reason next to the code, e.g. ``https_required`` for WEBHOOK_URL_INVALID.
        self.reason = reason
        # Transaction created before the error, when the API returned one (``transactionId``, e.g. a declined
        # charge on a saved card or a declined payment) - use it to query the transaction.
        self.transaction_id = transaction_id
        # Card decline details: ``cardError`` of a Payments API error, ``error`` of a declined card
        # operation.
        self.card_error = card_error


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
        reset: int | None = None,
    ) -> None:
        super().__init__(message, http_status, None, {}, raw_body)
        self.retry_after = retry_after
        self.limit = limit
        self.remaining = remaining
        # Unix time (seconds) when the limit resets - the ``X-RateLimit-Reset`` header.
        self.reset = reset


class PaymentRejectedError(ApiError):
    def __init__(
        self,
        message: str,
        http_status: int,
        error_code: str | None = None,
        field_errors: dict[str, list[str]] | None = None,
        raw_body: str = "",
        transaction_id: str | None = None,
        error_description: str | None = None,
    ) -> None:
        super().__init__(
            message, http_status, error_code, field_errors, raw_body, transaction_id=transaction_id
        )
        # Provider's description of the decline, when it sent one.
        self.error_description = error_description

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> PaymentRejectedError:
        raw_message = data.get("msg")
        message = raw_message if isinstance(raw_message, str) else "Payment rejected"
        additional = data.get("additionalInfo")
        additional = additional if isinstance(additional, dict) else {}
        raw_code = additional.get("error")
        error_code = raw_code if isinstance(raw_code, str) else None
        raw_description = additional.get("error_description")
        transaction_id = data.get("transactionId")
        return cls(
            message,
            200,
            error_code,
            {},
            php_json_encode(data),
            php_strval(transaction_id) if is_scalar(transaction_id) else None,
            raw_description if isinstance(raw_description, str) else None,
        )


class CardPaymentError(ApiError):
    """A card operation answered HTTP 200 with ``success: false``.

    ``message`` and ``error_code`` are the API ``message`` (e.g. ``DCC_OFFER_EXPIRED``); ``card_error`` holds
    the decline details (``error``) when the decline carries a recognised code.
    """

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> CardPaymentError:
        from dpay.card.card_error import CardError

        raw_message = data.get("message")
        message = raw_message if isinstance(raw_message, str) else "Card payment failed"
        error = data.get("error")
        return cls(
            message,
            200,
            message,
            {},
            php_json_encode(data),
            card_error=CardError.from_api(error) if isinstance(error, dict) else None,
        )
