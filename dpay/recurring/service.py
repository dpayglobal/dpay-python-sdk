from __future__ import annotations

from typing import cast

from dpay._internal.requestor import ApiRequestor, AsyncApiRequestor
from dpay.recurring import ops
from dpay.recurring.models import RecurringRetryResult, RecurringStatus


class RecurringService:
    """Recurring payments shared by payment methods (today BLIK).

    Registration and charges go through ``payments.register()`` with ``with_recurring_registration()``
    and ``with_recurring_alias()``.
    """

    def __init__(self, api: ApiRequestor) -> None:
        self._api = api

    def status(self, alias: str) -> RecurringStatus:
        """Current status and terms of the recurring payment registered for this service."""
        operation = ops.status(self._api.service, self._api.checksum, alias)
        return cast(RecurringStatus, self._api.execute(operation))

    def retry(self, transaction_id: str) -> RecurringRetryResult:
        """Retries a declined recurring charge (``transaction_id`` of that charge).

        Up to 3 times within 5 minutes, only after declines the customer can fix (e.g. INSUFFICIENT_FUNDS).
        Not retryable: ``InvalidRequestError`` with the code in ``field_errors["retry"]``
        (e.g. DECLINE_NOT_RETRYABLE, RETRY_LIMIT_REACHED).
        """
        operation = ops.retry(self._api.service, self._api.checksum, transaction_id)
        return cast(RecurringRetryResult, self._api.execute(operation))

    def cancel(self, alias: str, reason: str | None = None) -> str:
        """Cancels the recurring payment (for BLIK: unregisters the alias) and returns the new status."""
        operation = ops.cancel(self._api.service, self._api.checksum, alias, reason)
        return cast(str, self._api.execute(operation))


class AsyncRecurringService:
    def __init__(self, api: AsyncApiRequestor) -> None:
        self._api = api

    async def status(self, alias: str) -> RecurringStatus:
        operation = ops.status(self._api.service, self._api.checksum, alias)
        return cast(RecurringStatus, await self._api.execute(operation))

    async def retry(self, transaction_id: str) -> RecurringRetryResult:
        operation = ops.retry(self._api.service, self._api.checksum, transaction_id)
        return cast(RecurringRetryResult, await self._api.execute(operation))

    async def cancel(self, alias: str, reason: str | None = None) -> str:
        operation = ops.cancel(self._api.service, self._api.checksum, alias, reason)
        return cast(str, await self._api.execute(operation))
