from __future__ import annotations

from typing import Protocol, runtime_checkable

from dpay.http.models import ApiRequest, ApiResponse


@runtime_checkable
class HttpClient(Protocol):
    def request(self, request: ApiRequest) -> ApiResponse: ...


@runtime_checkable
class AsyncHttpClient(Protocol):
    async def request(self, request: ApiRequest) -> ApiResponse: ...
