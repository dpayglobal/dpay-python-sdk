from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from dpay._internal.base_urls import BaseUrls
from dpay._internal.php import is_php_int
from dpay.exceptions import DPayValueError

KNOWN_OPTIONS = ("service", "secret_hash", "timeout", "http_client", "base_urls")

DEFAULT_TIMEOUT = 30


class Config:
    def __init__(
        self,
        service: str,
        secret_hash: str,
        timeout: int,
        http_client: Any,
        base_urls: BaseUrls,
    ) -> None:
        self.service = service
        self.secret_hash = secret_hash
        self.timeout = timeout
        self.http_client = http_client
        self.base_urls = base_urls

    @classmethod
    def from_dict(cls, options: Mapping[str, Any]) -> Config:
        for key in options:
            if key not in KNOWN_OPTIONS:
                raise DPayValueError(f'Unknown option "{key}"')

        service = options.get("service")
        if not isinstance(service, str) or service == "":
            raise DPayValueError('Option "service" is required and must be a non-empty string')

        secret_hash = options.get("secret_hash")
        if not isinstance(secret_hash, str) or secret_hash == "":
            raise DPayValueError('Option "secret_hash" is required and must be a non-empty string')

        timeout = options.get("timeout")
        timeout = DEFAULT_TIMEOUT if timeout is None else timeout
        if not is_php_int(timeout) or timeout < 1:
            raise DPayValueError('Option "timeout" must be a positive integer')

        http_client = options.get("http_client")
        if http_client is not None and not callable(getattr(http_client, "request", None)):
            raise DPayValueError('Option "http_client" must implement HttpClient')

        overrides = options.get("base_urls")
        overrides = {} if overrides is None else overrides
        if not isinstance(overrides, Mapping):
            raise DPayValueError('Option "base_urls" must be a mapping')
        normalized: dict[str, str] = {}
        for host, url in overrides.items():
            if not isinstance(url, str) or url == "":
                raise DPayValueError("Base URLs must be non-empty strings")
            normalized[str(host)] = url

        return cls(service, secret_hash, timeout, http_client, BaseUrls(normalized))
