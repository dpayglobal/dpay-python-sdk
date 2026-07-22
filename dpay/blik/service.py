from __future__ import annotations

from typing import cast

from dpay._internal.requestor import ApiRequestor, AsyncApiRequestor
from dpay.blik import ops
from dpay.blik.enums import BlikAliasType
from dpay.blik.models import BlikAlias, BlikRecurringStatus


class BlikService:
    def __init__(self, api: ApiRequestor) -> None:
        self._api = api

    def alias(self, alias_value: str, alias_type: str = BlikAliasType.UID) -> BlikAlias:
        operation = ops.alias(self._api.service, self._api.checksum, alias_value, alias_type)
        return cast(BlikAlias, self._api.execute(operation))

    def unregister_alias(
        self,
        alias_value: str,
        alias_type: str = BlikAliasType.UID,
        reason: str | None = None,
    ) -> None:
        operation = ops.unregister_alias(
            self._api.service, self._api.checksum, alias_value, alias_type, reason
        )
        self._api.execute(operation)

    def recurring_status(self, alias_value: str) -> BlikRecurringStatus:
        operation = ops.recurring_status(self._api.service, self._api.checksum, alias_value)
        return cast(BlikRecurringStatus, self._api.execute(operation))


class AsyncBlikService:
    def __init__(self, api: AsyncApiRequestor) -> None:
        self._api = api

    async def alias(self, alias_value: str, alias_type: str = BlikAliasType.UID) -> BlikAlias:
        operation = ops.alias(self._api.service, self._api.checksum, alias_value, alias_type)
        return cast(BlikAlias, await self._api.execute(operation))

    async def unregister_alias(
        self,
        alias_value: str,
        alias_type: str = BlikAliasType.UID,
        reason: str | None = None,
    ) -> None:
        operation = ops.unregister_alias(
            self._api.service, self._api.checksum, alias_value, alias_type, reason
        )
        await self._api.execute(operation)

    async def recurring_status(self, alias_value: str) -> BlikRecurringStatus:
        operation = ops.recurring_status(self._api.service, self._api.checksum, alias_value)
        return cast(BlikRecurringStatus, await self._api.execute(operation))
