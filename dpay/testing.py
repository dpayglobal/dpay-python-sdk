from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from dpay._internal.php import php_json_encode
from dpay.http.models import ApiRequest, ApiResponse


class MockHttpClient:
    def __init__(self) -> None:
        self.queued: list[ApiResponse] = []
        self.requests: list[ApiRequest] = []

    def queue(self, response: ApiResponse) -> None:
        self.queued.append(response)

    def queue_json(self, status: int, body: Any, headers: Mapping[str, str] | None = None) -> None:
        merged = {"content-type": "application/json", **(headers or {})}
        self.queue(ApiResponse(status, merged, php_json_encode(body)))

    def queue_text(self, status: int, body: str, headers: Mapping[str, str] | None = None) -> None:
        self.queue(ApiResponse(status, headers or {}, body))

    def request(self, request: ApiRequest) -> ApiResponse:
        self.requests.append(request)
        if not self.queued:
            raise AssertionError("MockHttpClient queue is empty")
        return self.queued.pop(0)

    @property
    def last_request(self) -> ApiRequest:
        if not self.requests:
            raise AssertionError("No requests recorded")
        return self.requests[-1]

    @property
    def last_request_body(self) -> dict[str, Any]:
        body = self.last_request.body
        decoded = json.loads(body) if body is not None else None
        if not isinstance(decoded, dict):
            raise AssertionError("Last request has no JSON object body")
        return decoded


class MockAsyncHttpClient(MockHttpClient):
    async def request(self, request: ApiRequest) -> ApiResponse:  # type: ignore[override]
        return super().request(request)
