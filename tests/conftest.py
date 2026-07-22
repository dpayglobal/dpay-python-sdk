from __future__ import annotations

import pytest

from dpay import DPayClient
from dpay.aio import AsyncDPayClient
from dpay.testing import MockAsyncHttpClient, MockHttpClient

SERVICE = "test_service"
SECRET = "sekret-hash-123"


@pytest.fixture
def transport() -> MockHttpClient:
    return MockHttpClient()


@pytest.fixture
def client(transport: MockHttpClient) -> DPayClient:
    return DPayClient(service=SERVICE, secret_hash=SECRET, http_client=transport)


@pytest.fixture
def async_transport() -> MockAsyncHttpClient:
    return MockAsyncHttpClient()


@pytest.fixture
def async_client(async_transport: MockAsyncHttpClient) -> AsyncDPayClient:
    return AsyncDPayClient(service=SERVICE, secret_hash=SECRET, http_client=async_transport)
