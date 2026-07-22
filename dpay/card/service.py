from __future__ import annotations

from typing import cast

from dpay._internal.requestor import ApiRequestor, AsyncApiRequestor
from dpay.card import ops
from dpay.card.requests import ApplePayRequest, CardPaymentRequest, GooglePayRequest
from dpay.card.results import CardPaymentResult
from dpay.money import Money


class CardService:
    def __init__(self, api: ApiRequestor) -> None:
        self._api = api

    def public_key(self) -> str:
        return cast(str, self._api.execute(ops.public_key()))

    def pay_otp(self, transaction_id: str, request: CardPaymentRequest) -> CardPaymentResult:
        return cast(CardPaymentResult, self._api.execute(ops.pay_otp(transaction_id, request)))

    def pre_auth(self, transaction_id: str, request: CardPaymentRequest) -> CardPaymentResult:
        return cast(CardPaymentResult, self._api.execute(ops.pre_auth(transaction_id, request)))

    def capture(self, transaction_id: str, amount: Money | None = None) -> CardPaymentResult:
        return cast(CardPaymentResult, self._api.execute(ops.capture(transaction_id, amount)))

    def cancel(self, transaction_id: str, amount: Money | None = None) -> CardPaymentResult:
        return cast(CardPaymentResult, self._api.execute(ops.cancel(transaction_id, amount)))

    def google_pay(self, transaction_id: str, request: GooglePayRequest) -> CardPaymentResult:
        return cast(CardPaymentResult, self._api.execute(ops.google_pay(transaction_id, request)))

    def apple_pay(self, transaction_id: str, request: ApplePayRequest) -> CardPaymentResult:
        return cast(CardPaymentResult, self._api.execute(ops.apple_pay(transaction_id, request)))


class AsyncCardService:
    def __init__(self, api: AsyncApiRequestor) -> None:
        self._api = api

    async def public_key(self) -> str:
        return cast(str, await self._api.execute(ops.public_key()))

    async def pay_otp(self, transaction_id: str, request: CardPaymentRequest) -> CardPaymentResult:
        return cast(CardPaymentResult, await self._api.execute(ops.pay_otp(transaction_id, request)))

    async def pre_auth(self, transaction_id: str, request: CardPaymentRequest) -> CardPaymentResult:
        return cast(CardPaymentResult, await self._api.execute(ops.pre_auth(transaction_id, request)))

    async def capture(self, transaction_id: str, amount: Money | None = None) -> CardPaymentResult:
        return cast(CardPaymentResult, await self._api.execute(ops.capture(transaction_id, amount)))

    async def cancel(self, transaction_id: str, amount: Money | None = None) -> CardPaymentResult:
        return cast(CardPaymentResult, await self._api.execute(ops.cancel(transaction_id, amount)))

    async def google_pay(self, transaction_id: str, request: GooglePayRequest) -> CardPaymentResult:
        return cast(CardPaymentResult, await self._api.execute(ops.google_pay(transaction_id, request)))

    async def apple_pay(self, transaction_id: str, request: ApplePayRequest) -> CardPaymentResult:
        return cast(CardPaymentResult, await self._api.execute(ops.apple_pay(transaction_id, request)))
