from __future__ import annotations

from typing import Any
from urllib.parse import quote

from dpay._internal import base_urls
from dpay._internal.checksum import ChecksumCalculator
from dpay._internal.operation import Operation, decode_dict_or_fail
from dpay.card.requests import ApplePayRequest, CardPaymentRequest, GooglePayRequest
from dpay.card.results import CardPaymentResult
from dpay.exceptions import CardPaymentError
from dpay.http.models import ApiResponse
from dpay.money import Money
from dpay.webhook.event_type import WebhookEventType
from dpay.webhook.target import WebhookTarget


def public_key() -> Operation:
    return Operation(
        "GET",
        base_urls.API_PAYMENTS,
        "/api/v1_0/cards/public-key",
        lambda response: response.body.strip(),
    )


def _payment(transaction_id: str, suffix: str, body: dict[str, Any]) -> Operation:
    path = f"/api/v1_0/cards/payment/{quote(transaction_id, safe='')}{suffix}"
    return Operation("POST", base_urls.API_PAYMENTS, path, _parse_result, body)


def _parse_result(response: ApiResponse) -> CardPaymentResult:
    data = decode_dict_or_fail(response)
    if data.get("success", False) is not True:
        raise CardPaymentError.from_api(data)
    return CardPaymentResult.from_api(data)


def pay_otp(transaction_id: str, request: CardPaymentRequest) -> Operation:
    return _payment(transaction_id, "/pay/card-otp", request.to_api())


def pre_auth(transaction_id: str, request: CardPaymentRequest) -> Operation:
    return _payment(transaction_id, "/pay/card-pre-auth", request.to_api())


def capture(
    service: str,
    checksum: ChecksumCalculator,
    transaction_id: str,
    amount: Money,
    webhook: WebhookTarget | None = None,
) -> Operation:
    body: dict[str, Any] = {"service": service, "amount": float(amount.to_decimal())}
    if webhook is not None:
        webhook.assert_events_allowed(WebhookEventType.CAPTURE, "a card capture")
        body["webhook"] = webhook.to_api()
    # sha256(capture|service|transaction_id|amount|hash) - the webhook object stays out of the checksum
    body["checksum"] = checksum.operation("capture", service, transaction_id, amount.to_decimal())
    return _payment(transaction_id, "/capture", body)


def cancel(
    service: str, checksum: ChecksumCalculator, transaction_id: str, amount: Money | None
) -> Operation:
    body: dict[str, Any] = {"service": service}
    if amount is not None:
        body["amount"] = float(amount.to_decimal())
    # sha256(cancellation|service|transaction_id|amount|hash) - empty amount segment without an amount
    body["checksum"] = checksum.operation(
        "cancellation", service, transaction_id, None if amount is None else amount.to_decimal()
    )
    return _payment(transaction_id, "/cancellation", body)


def google_pay(transaction_id: str, request: GooglePayRequest) -> Operation:
    return _payment(transaction_id, "/pay/google-pay", request.to_api())


def apple_pay(transaction_id: str, request: ApplePayRequest) -> Operation:
    return _payment(transaction_id, "/pay/apple-pay", request.to_api())
