from __future__ import annotations

import urllib.error
import urllib.request

from dpay.exceptions import TransportError
from dpay.http.models import ApiRequest, ApiResponse

DEFAULT_TIMEOUT = 30


class UrllibHttpClient:
    def __init__(self, timeout: int = DEFAULT_TIMEOUT) -> None:
        self._timeout = timeout

    def request(self, request: ApiRequest) -> ApiResponse:
        payload = request.body.encode("utf-8") if request.body is not None else None
        native = urllib.request.Request(
            request.url,
            data=payload,
            headers=dict(request.headers),
            method=request.method,
        )
        try:
            with urllib.request.urlopen(native, timeout=self._timeout) as response:
                return ApiResponse(
                    response.status,
                    dict(response.headers.items()),
                    response.read().decode("utf-8", "replace"),
                )
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", "replace")
            return ApiResponse(error.code, dict(error.headers.items()), body)
        except urllib.error.URLError as error:
            raise TransportError(f"HTTP request failed: {error.reason}") from error
        except OSError as error:
            raise TransportError(f"HTTP request failed: {error}") from error
