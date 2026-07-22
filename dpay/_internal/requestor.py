from __future__ import annotations

import platform
from typing import Any

from dpay._internal.base_urls import BaseUrls
from dpay._internal.checksum import ChecksumCalculator
from dpay._internal.error_mapper import map_error
from dpay._internal.operation import Operation
from dpay._internal.php import php_json_encode
from dpay.config import Config
from dpay.exceptions import TransportError
from dpay.http.base import AsyncHttpClient, HttpClient
from dpay.http.models import ApiRequest, ApiResponse
from dpay.version import SDK_VERSION

USER_AGENT = f"dpay-python-sdk/{SDK_VERSION} python/{platform.python_version()}"


class _RequestorBase:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.checksum = ChecksumCalculator(config.secret_hash)
        self.base_urls: BaseUrls = config.base_urls

    @property
    def service(self) -> str:
        return self.config.service

    def build_request(self, operation: Operation) -> ApiRequest:
        url = self.base_urls.resolve(operation.host) + operation.path
        headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
        encoded: str | None = None
        if operation.body is not None:
            headers["Content-Type"] = "application/json"
            try:
                encoded = php_json_encode(operation.body)
            except (TypeError, ValueError) as error:
                raise TransportError("Unable to encode request body as JSON") from error
        return ApiRequest(operation.method, url, headers, encoded)

    def finish(self, operation: Operation, response: ApiResponse) -> Any:
        if operation.raise_for_status and response.status >= 400:
            raise map_error(response)
        return operation.parse(response)


class ApiRequestor(_RequestorBase):
    def __init__(self, config: Config, http_client: HttpClient) -> None:
        super().__init__(config)
        self.http_client = http_client

    def execute(self, operation: Operation) -> Any:
        response = self.http_client.request(self.build_request(operation))
        return self.finish(operation, response)


class AsyncApiRequestor(_RequestorBase):
    def __init__(self, config: Config, http_client: AsyncHttpClient) -> None:
        super().__init__(config)
        self.http_client = http_client

    async def execute(self, operation: Operation) -> Any:
        response = await self.http_client.request(self.build_request(operation))
        return self.finish(operation, response)
