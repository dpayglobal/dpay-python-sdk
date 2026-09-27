from __future__ import annotations

from typing import cast

from dpay._internal.requestor import ApiRequestor, AsyncApiRequestor
from dpay.money import Money
from dpay.refund import ops
from dpay.refund.models import Refund, RefundAvailability
from dpay.webhook.target import WebhookTarget


class RefundService:
    def __init__(self, api: ApiRequestor) -> None:
        self._api = api

    def create(
        self,
        transaction_id: str,
        amount: Money | None = None,
        reason: str | None = None,
        webhook: WebhookTarget | None = None,
    ) -> Refund:
        """Orders a refund (partial with an amount, the rest of the payment without).

        An accepted refund is not a finished one - its outcome comes as a ``refund.succeeded`` or
        ``refund.failed`` event. The optional webhook target receives the events of this refund and is
        part of the checksum.
        """
        operation = ops.create(self._api.service, self._api.checksum, transaction_id, amount, reason, webhook)
        return cast(Refund, self._api.execute(operation))

    def check_availability(
        self, transaction_id: str, amount: Money | None = None, reason: str | None = None
    ) -> RefundAvailability:
        operation = ops.check_availability(
            self._api.service, self._api.checksum, transaction_id, amount, reason
        )
        return cast(RefundAvailability, self._api.execute(operation))


class AsyncRefundService:
    def __init__(self, api: AsyncApiRequestor) -> None:
        self._api = api

    async def create(
        self,
        transaction_id: str,
        amount: Money | None = None,
        reason: str | None = None,
        webhook: WebhookTarget | None = None,
    ) -> Refund:
        operation = ops.create(self._api.service, self._api.checksum, transaction_id, amount, reason, webhook)
        return cast(Refund, await self._api.execute(operation))

    async def check_availability(
        self, transaction_id: str, amount: Money | None = None, reason: str | None = None
    ) -> RefundAvailability:
        operation = ops.check_availability(
            self._api.service, self._api.checksum, transaction_id, amount, reason
        )
        return cast(RefundAvailability, await self._api.execute(operation))
