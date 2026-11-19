from __future__ import annotations

from typing import cast

from dpay._internal.requestor import ApiRequestor, AsyncApiRequestor
from dpay.money import Money
from dpay.refund import ops
from dpay.refund.models import Refund, RefundAvailability
from dpay.webhook.target import WebhookTarget


class RefundService:
    # Request header with your own refund identifier; it sets the refund transfer title.
    MESSAGE_ID_HEADER = ops.MESSAGE_ID_HEADER

    def __init__(self, api: ApiRequestor) -> None:
        self._api = api

    def create(
        self,
        transaction_id: str,
        amount: Money | None = None,
        reason: str | None = None,
        webhook: WebhookTarget | None = None,
        message_id: str | None = None,
    ) -> Refund:
        """Orders a refund (partial with an amount, the rest of the payment without).

        An accepted refund is not a finished one - its outcome comes as a ``refund.succeeded`` or
        ``refund.failed`` event. The optional webhook target receives the events of this refund and is
        part of the checksum. The transaction ID, reason and webhook URL are sent and signed trimmed, as the
        API trims them before it verifies the checksum; a reason that is blank after trimming is sent as
        ``""`` and a blank transaction ID raises ``DPayValueError``.

        ``message_id`` - your own refund identifier, sent in the ``DigitalPayments-PSP-Message-ID`` header
        (not part of the checksum): the refund transfer title becomes ``dpay.pl zwrot {message_id}`` and
        ``Refund.message`` returns it. Printable ASCII; the API keeps the first 24 characters.
        """
        operation = ops.create(
            self._api.service, self._api.checksum, transaction_id, amount, reason, webhook, message_id
        )
        return cast(Refund, self._api.execute(operation))

    def check_availability(
        self, transaction_id: str, amount: Money | None = None, reason: str | None = None
    ) -> RefundAvailability:
        """Checks whether the refund is possible.

        The answer is decided by the body, not by a list of statuses: HTTP 200 and every 4xx whose JSON
        body carries the ``refund`` key are returned as ``RefundAvailability`` (``http_status`` tells the
        reason apart) - today the business refusals 400, 402, 404 (transaction does not exist), 406, 409,
        410, 411, 423 and a business 401. Raised: 401 "Unauthorized request" (invalid checksum), every
        response without the ``refund`` key - which is how the API answers validation errors (422) and
        rate limits (429) - and every 5xx, even with the ``refund`` key.
        """
        operation = ops.check_availability(
            self._api.service, self._api.checksum, transaction_id, amount, reason
        )
        return cast(RefundAvailability, self._api.execute(operation))


class AsyncRefundService:
    MESSAGE_ID_HEADER = ops.MESSAGE_ID_HEADER

    def __init__(self, api: AsyncApiRequestor) -> None:
        self._api = api

    async def create(
        self,
        transaction_id: str,
        amount: Money | None = None,
        reason: str | None = None,
        webhook: WebhookTarget | None = None,
        message_id: str | None = None,
    ) -> Refund:
        operation = ops.create(
            self._api.service, self._api.checksum, transaction_id, amount, reason, webhook, message_id
        )
        return cast(Refund, await self._api.execute(operation))

    async def check_availability(
        self, transaction_id: str, amount: Money | None = None, reason: str | None = None
    ) -> RefundAvailability:
        operation = ops.check_availability(
            self._api.service, self._api.checksum, transaction_id, amount, reason
        )
        return cast(RefundAvailability, await self._api.execute(operation))
