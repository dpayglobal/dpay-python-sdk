from __future__ import annotations

from typing import cast

from dpay._internal.requestor import ApiRequestor, AsyncApiRequestor
from dpay.payout import ops
from dpay.payout.models import PayoutDetails


class PayoutService:
    def __init__(self, api: ApiRequestor) -> None:
        self._api = api

    def details(self, withdraw_id: int, timestamp: int | None = None) -> PayoutDetails:
        operation = ops.details(self._api.service, self._api.checksum, withdraw_id, timestamp)
        return cast(PayoutDetails, self._api.execute(operation))


class AsyncPayoutService:
    def __init__(self, api: AsyncApiRequestor) -> None:
        self._api = api

    async def details(self, withdraw_id: int, timestamp: int | None = None) -> PayoutDetails:
        operation = ops.details(self._api.service, self._api.checksum, withdraw_id, timestamp)
        return cast(PayoutDetails, await self._api.execute(operation))
