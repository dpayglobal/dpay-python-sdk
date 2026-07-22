from __future__ import annotations

from typing import Any

from dpay._internal import base_urls
from dpay._internal.checksum import ChecksumCalculator
from dpay._internal.operation import Operation, decode_dict_or_fail
from dpay._internal.php import is_scalar, php_strval
from dpay.exceptions import PaymentRejectedError
from dpay.http.models import ApiResponse
from dpay.payment.models import RegisteredPayment, Transaction
from dpay.payment.register_request import RegisterPaymentRequest


def _string_field(body: dict[str, Any], key: str) -> str:
    value = body.get(key)
    return php_strval(value) if is_scalar(value) else ""


def register(service: str, checksum: ChecksumCalculator, request: RegisterPaymentRequest) -> Operation:
    body = request.to_api(service)
    body["checksum"] = checksum.secret_second(
        service,
        [
            _string_field(body, "value"),
            _string_field(body, "url_success"),
            _string_field(body, "url_fail"),
            _string_field(body, "url_ipn"),
        ],
    )
    return Operation(
        "POST",
        base_urls.API_PAYMENTS,
        "/api/v1_0/payments/register",
        _parse_register,
        body,
    )


def _parse_register(response: ApiResponse) -> RegisteredPayment:
    data = decode_dict_or_fail(response)
    if data.get("error", False) is True or data.get("status", True) is False:
        raise PaymentRejectedError.from_api(data)
    return RegisteredPayment.from_api(data)


def details(service: str, checksum: ChecksumCalculator, transaction_id: str) -> Operation:
    body: dict[str, Any] = {"service": service, "transaction_id": transaction_id}
    body["checksum"] = checksum.ordered_body(list(body.values()))
    return Operation(
        "POST",
        base_urls.PANEL,
        "/api/v1/pbl/details",
        lambda response: Transaction.from_api(decode_dict_or_fail(response)),
        body,
    )
