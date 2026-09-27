from __future__ import annotations

from typing import cast

from dpay._internal.requestor import ApiRequestor, AsyncApiRequestor
from dpay.blik import ops
from dpay.blik.enums import BlikAliasType
from dpay.blik.models import BlikAlias


class BlikService:
    """BLIK OneClick aliases (UID). Recurring payments are handled by ``DPayClient.recurring``."""

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
