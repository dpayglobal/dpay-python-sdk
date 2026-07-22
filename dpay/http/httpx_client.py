from __future__ import annotations

from typing import Any

from dpay.exceptions import DPayError, TransportError
from dpay.http.models import ApiRequest, ApiResponse

DEFAULT_TIMEOUT = 30
CONNECT_TIMEOUT = 10


def _load_httpx() -> Any:
    try:
        import httpx
    except ImportError as error:
        raise DPayError(
            'The async client requires httpx. Install it with: pip install "dpay-python-sdk[async]"'
        ) from error
    return httpx


class HttpxAsyncHttpClient:
    def __init__(self, timeout: int = DEFAULT_TIMEOUT, client: Any = None) -> None:
        httpx = _load_httpx()
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=CONNECT_TIMEOUT))
        self._request_error = httpx.RequestError

    async def request(self, request: ApiRequest) -> ApiResponse:
        try:
            response = await self._client.request(
                request.method,
                request.url,
                headers=dict(request.headers),
                content=request.body.encode("utf-8") if request.body is not None else None,
            )
        except self._request_error as error:
            raise TransportError(f"HTTP request failed: {error}") from error
        return ApiResponse(response.status_code, dict(response.headers), response.text)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
