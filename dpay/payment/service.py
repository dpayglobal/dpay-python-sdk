from __future__ import annotations

from typing import cast

from dpay._internal.requestor import ApiRequestor, AsyncApiRequestor
from dpay.payment import ops
from dpay.payment.models import RegisteredPayment, Transaction
from dpay.payment.register_request import RegisterPaymentRequest


class PaymentService:
    def __init__(self, api: ApiRequestor) -> None:
        self._api = api

    def register(self, request: RegisterPaymentRequest) -> RegisteredPayment:
        operation = ops.register(self._api.service, self._api.checksum, request)
        return cast(RegisteredPayment, self._api.execute(operation))

    def details(self, transaction_id: str) -> Transaction:
        operation = ops.details(self._api.service, self._api.checksum, transaction_id)
        return cast(Transaction, self._api.execute(operation))


class AsyncPaymentService:
    def __init__(self, api: AsyncApiRequestor) -> None:
        self._api = api

    async def register(self, request: RegisterPaymentRequest) -> RegisteredPayment:
        operation = ops.register(self._api.service, self._api.checksum, request)
        return cast(RegisteredPayment, await self._api.execute(operation))

    async def details(self, transaction_id: str) -> Transaction:
        operation = ops.details(self._api.service, self._api.checksum, transaction_id)
        return cast(Transaction, await self._api.execute(operation))
