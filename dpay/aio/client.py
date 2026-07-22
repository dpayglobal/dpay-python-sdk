from __future__ import annotations

from collections.abc import Mapping
from types import TracebackType
from typing import Any

from dpay._internal.requestor import AsyncApiRequestor
from dpay.bank.service import AsyncBankService
from dpay.blik.service import AsyncBlikService
from dpay.card.service import AsyncCardService
from dpay.config import Config
from dpay.http.base import AsyncHttpClient
from dpay.http.httpx_client import HttpxAsyncHttpClient
from dpay.payment.service import AsyncPaymentService
from dpay.payout.service import AsyncPayoutService
from dpay.refund.service import AsyncRefundService
from dpay.version import SDK_VERSION


class AsyncDPayClient:
    VERSION = SDK_VERSION

    def __init__(
        self,
        *,
        service: str | None = None,
        secret_hash: str | None = None,
        timeout: int | None = None,
        http_client: AsyncHttpClient | None = None,
        base_urls: Mapping[str, str] | None = None,
        **extra: Any,
    ) -> None:
        options: dict[str, Any] = dict(extra)
        options["service"] = service
        options["secret_hash"] = secret_hash
        options["timeout"] = timeout
        options["http_client"] = http_client
        options["base_urls"] = base_urls

        self.config = Config.from_dict(options)
        transport = self.config.http_client or HttpxAsyncHttpClient(self.config.timeout)
        self._transport = transport
        api = AsyncApiRequestor(self.config, transport)

        self.payments = AsyncPaymentService(api)
        self.refunds = AsyncRefundService(api)
        self.banks = AsyncBankService(api)
        self.blik = AsyncBlikService(api)
        self.cards = AsyncCardService(api)
        self.payouts = AsyncPayoutService(api)

    async def aclose(self) -> None:
        closer = getattr(self._transport, "aclose", None)
        if callable(closer):
            await closer()

    async def __aenter__(self) -> AsyncDPayClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()
