from __future__ import annotations

import pytest

from dpay import DPayError, DPayValueError, Money, RegisterPaymentRequest, ReturnUrls, TransactionType
from dpay.aio import AsyncDPayClient
from dpay.testing import MockAsyncHttpClient
from tests.conftest import SECRET, SERVICE
from tests.scenario import build_device_info

URLS = ReturnUrls("https://shop.test/ok", "https://shop.test/fail", "https://shop.test/ipn")


def _request() -> RegisterPaymentRequest:
    return RegisterPaymentRequest.create(Money.pln(1050), TransactionType.TRANSFERS, URLS)


async def test_register_matches_sync_wire_format(
    async_client: AsyncDPayClient, async_transport: MockAsyncHttpClient
) -> None:
    from dpay import DPayClient
    from dpay.testing import MockHttpClient

    async_transport.queue_json(200, {"transactionId": "tx-1", "msg": "ok"})
    await async_client.payments.register(_request())

    sync_transport = MockHttpClient()
    sync_transport.queue_json(200, {"transactionId": "tx-1", "msg": "ok"})
    DPayClient(service=SERVICE, secret_hash=SECRET, http_client=sync_transport).payments.register(_request())

    assert async_transport.last_request.body == sync_transport.last_request.body
    assert async_transport.last_request.url == sync_transport.last_request.url


async def test_all_services_are_available(
    async_client: AsyncDPayClient, async_transport: MockAsyncHttpClient
) -> None:
    async_transport.queue_json(200, {"transaction": {"id": "tx-1", "status": "paid"}})
    assert (await async_client.payments.details("tx-1")).is_paid

    async_transport.queue_json(200, {"status": "success", "refund": True})
    assert (await async_client.refunds.create("tx-1")).is_accepted

    async_transport.queue_json(200, {"refund": True})
    assert (await async_client.refunds.check_availability("tx-1")).is_available

    async_transport.queue_json(200, [{"id": "1", "name": "Bank"}])
    assert (await async_client.banks.all())[0].name == "Bank"

    async_transport.queue_json(200, [])
    assert await async_client.banks.for_service(1) == []

    async_transport.queue_json(200, {"id": 1, "state": 1})
    assert (await async_client.payouts.details(1)).is_processed

    async_transport.queue_json(200, {"data": {"alias_value": "a-1", "status": "ACTIVE"}})
    assert (await async_client.blik.alias("a-1")).is_active

    async_transport.queue_json(200, {"data": {}})
    await async_client.blik.unregister_alias("a-1")

    async_transport.queue_json(200, {"data": {"alias_value": "a-1"}})
    assert (await async_client.blik.recurring_status("a-1")).alias_value == "a-1"

    async_transport.queue_text(200, " key ")
    assert await async_client.cards.public_key() == "key"

    async_transport.queue_json(200, {"success": True, "message": {"redirectType": "SUCCESS"}})
    assert (await async_client.cards.capture("tx-1", Money.pln(1))).is_success


async def test_card_endpoints(async_client: AsyncDPayClient, async_transport: MockAsyncHttpClient) -> None:
    from dpay import ApplePayRequest, CardPaymentRequest, GooglePayRequest

    device = build_device_info()
    for _ in range(5):
        async_transport.queue_json(200, {"success": True, "message": {"redirectType": "SUCCESS"}})

    assert (await async_client.cards.pay_otp("t", CardPaymentRequest.create(device))).is_success
    assert (await async_client.cards.pre_auth("t", CardPaymentRequest.create(device))).is_success
    assert (await async_client.cards.cancel("t")).is_success
    assert (await async_client.cards.google_pay("t", GooglePayRequest.create("tok", device))).is_success
    assert (await async_client.cards.apple_pay("t", ApplePayRequest.init(device))).is_success


async def test_errors_propagate(async_client: AsyncDPayClient, async_transport: MockAsyncHttpClient) -> None:
    from dpay import NotFoundError

    async_transport.queue_json(404, {"message": "nie ma"})
    with pytest.raises(NotFoundError):
        await async_client.payments.details("brak")


async def test_context_manager_closes_transport() -> None:
    transport = MockAsyncHttpClient()
    async with AsyncDPayClient(service=SERVICE, secret_hash=SECRET, http_client=transport) as client:
        transport.queue_json(200, {"transaction": {"id": "t"}})
        await client.payments.details("t")


def test_config_validation_is_shared() -> None:
    with pytest.raises(DPayValueError, match='Option "service" is required'):
        AsyncDPayClient(secret_hash="h")


def test_missing_httpx_gives_actionable_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "httpx":
            raise ImportError("no httpx")
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(DPayError, match="dpay-python-sdk\\[async\\]"):
        AsyncDPayClient(service=SERVICE, secret_hash=SECRET)
