from __future__ import annotations

from typing import cast

from dpay._internal.requestor import ApiRequestor, AsyncApiRequestor
from dpay.bank import ops
from dpay.bank.models import Bank


class BankService:
    def __init__(self, api: ApiRequestor) -> None:
        self._api = api

    def all(self) -> list[Bank]:
        return cast(list[Bank], self._api.execute(ops.all_banks()))

    def for_service(self, timestamp: int | None = None) -> list[Bank]:
        operation = ops.for_service(self._api.service, self._api.checksum, timestamp)
        return cast(list[Bank], self._api.execute(operation))


class AsyncBankService:
    def __init__(self, api: AsyncApiRequestor) -> None:
        self._api = api

    async def all(self) -> list[Bank]:
        return cast(list[Bank], await self._api.execute(ops.all_banks()))

    async def for_service(self, timestamp: int | None = None) -> list[Bank]:
        operation = ops.for_service(self._api.service, self._api.checksum, timestamp)
        return cast(list[Bank], await self._api.execute(operation))
