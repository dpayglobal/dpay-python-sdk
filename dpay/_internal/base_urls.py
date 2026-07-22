from __future__ import annotations

from collections.abc import Mapping

from dpay.exceptions import DPayValueError

API_PAYMENTS = "api_payments"
PANEL = "panel"
GATEWAY = "gateway"

_DEFAULTS = {
    API_PAYMENTS: "https://api-payments.dpay.pl",
    PANEL: "https://panel.dpay.pl",
    GATEWAY: "https://secure.dpay.pl",
}


class BaseUrls:
    API_PAYMENTS = API_PAYMENTS
    PANEL = PANEL
    GATEWAY = GATEWAY

    def __init__(self, overrides: Mapping[str, str] | None = None) -> None:
        overrides = overrides or {}
        for host in overrides:
            if host not in _DEFAULTS:
                raise DPayValueError(f'Unknown base URL key "{host}"')
        self._urls = dict(_DEFAULTS)
        for host, url in overrides.items():
            self._urls[host] = url.rstrip("/")

    def resolve(self, host: str) -> str:
        if host not in self._urls:
            raise DPayValueError(f'Unknown API host "{host}"')
        return self._urls[host]
