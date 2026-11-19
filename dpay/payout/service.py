from __future__ import annotations

from collections.abc import AsyncIterator, Iterator, Mapping
from typing import Any, cast

from dpay._internal.requestor import ApiRequestor, AsyncApiRequestor
from dpay.payout import ops
from dpay.payout.models import PayoutDetails, PayoutListItem, PayoutPage, PayoutSettlement


class PayoutService:
    """Payouts (withdrawals) of your account.

    Every endpoint signs the body in the order it is sent: ``sha256(value1|value2|...|secret_hash)`` -
    optional fields are sent only when set.
    """

    def __init__(self, api: ApiRequestor) -> None:
        self._api = api

    def details(self, withdraw_id: int, timestamp: int | None = None) -> PayoutDetails:
        operation = ops.details(self._api.service, self._api.checksum, withdraw_id, timestamp)
        return cast(PayoutDetails, self._api.execute(operation))

    def list(
        self, filters: Mapping[str, Any] | None = None, page: int | None = None, per_page: int | None = None
    ) -> PayoutPage:
        """Your payouts, newest first - the source of ``withdraw_id``.

        ``filters``: ``date_from`` and ``date_to`` (creation date range, any date or date-time, e.g.
        ``2026-07-01``, ``2026-07-31 23:59:59``; sent trimmed), ``state`` (``PayoutState``) and ``type``
        (``PayoutType``). ``per_page`` 1-200 (API default 50).
        """
        operation = ops.list_payouts(self._api.service, self._api.checksum, filters, page, per_page)
        return cast(PayoutPage, self._api.execute(operation))

    def iterate(
        self, filters: Mapping[str, Any] | None = None, per_page: int | None = None
    ) -> Iterator[PayoutListItem]:
        """All matching payouts page by page, newest first."""
        page = 1
        while True:
            result = self.list(filters, page, per_page)
            yield from result.items
            if not result.has_more:
                return
            page += 1

    def details_full(
        self, withdraw_id: int, page: int | None = None, per_page: int | None = None
    ) -> PayoutSettlement:
        """The payout with the payments it settles: header, totals of the whole settlement and one page of
        positions. ``per_page`` 1-500 (API default 100)."""
        operation = ops.details_full(self._api.service, self._api.checksum, withdraw_id, page, per_page)
        return cast(PayoutSettlement, self._api.execute(operation))


class AsyncPayoutService:
    def __init__(self, api: AsyncApiRequestor) -> None:
        self._api = api

    async def details(self, withdraw_id: int, timestamp: int | None = None) -> PayoutDetails:
        operation = ops.details(self._api.service, self._api.checksum, withdraw_id, timestamp)
        return cast(PayoutDetails, await self._api.execute(operation))

    async def list(
        self, filters: Mapping[str, Any] | None = None, page: int | None = None, per_page: int | None = None
    ) -> PayoutPage:
        operation = ops.list_payouts(self._api.service, self._api.checksum, filters, page, per_page)
        return cast(PayoutPage, await self._api.execute(operation))

    async def iterate(
        self, filters: Mapping[str, Any] | None = None, per_page: int | None = None
    ) -> AsyncIterator[PayoutListItem]:
        page = 1
        while True:
            result = await self.list(filters, page, per_page)
            for item in result.items:
                yield item
            if not result.has_more:
                return
            page += 1

    async def details_full(
        self, withdraw_id: int, page: int | None = None, per_page: int | None = None
    ) -> PayoutSettlement:
        operation = ops.details_full(self._api.service, self._api.checksum, withdraw_id, page, per_page)
        return cast(PayoutSettlement, await self._api.execute(operation))
