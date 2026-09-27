from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from dpay._internal.requestor import ApiRequestor
from dpay.bank.service import BankService
from dpay.blik.service import BlikService
from dpay.card.service import CardService
from dpay.config import Config
from dpay.http.base import HttpClient
from dpay.http.urllib_client import UrllibHttpClient
from dpay.payment.service import PaymentService
from dpay.payout.service import PayoutService
from dpay.recurring.service import RecurringService
from dpay.refund.service import RefundService
from dpay.version import SDK_VERSION
from dpay.webhook.service import EventService


class DPayClient:
    VERSION = SDK_VERSION

    def __init__(
        self,
        *,
        service: str | None = None,
        secret_hash: str | None = None,
        timeout: int | None = None,
        http_client: HttpClient | None = None,
        base_urls: Mapping[str, str] | None = None,
        **extra: Any,
    ) -> None:
        options: dict[str, Any] = dict(extra)
        options["service"] = service
        options["secret_hash"] = secret_hash
        options["timeout"] = timeout
        options["http_client"] = http_client
        options["base_urls"] = base_urls

        self.config = Config.from_dict(options)
        transport = self.config.http_client or UrllibHttpClient(self.config.timeout)
        api = ApiRequestor(self.config, transport)

        self.payments = PaymentService(api)
        self.refunds = RefundService(api)
        self.banks = BankService(api)
        self.blik = BlikService(api)
        self.cards = CardService(api)
        self.payouts = PayoutService(api)
        self.recurring = RecurringService(api)
        self.events = EventService(api)
