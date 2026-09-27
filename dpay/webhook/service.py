from __future__ import annotations

from collections.abc import AsyncIterator, Iterator, Sequence
from typing import cast

from dpay._internal.requestor import ApiRequestor, AsyncApiRequestor
from dpay.webhook import ops
from dpay.webhook.event import EventPage, WebhookEvent


class EventService:
    """Events API: the event history of the service (the same envelopes as webhooks), newest first.

    Use it to catch up after an outage of your webhook endpoint.
    """

    def __init__(self, api: ApiRequestor) -> None:
        self._api = api

    def list(
        self,
        *,
        types: Sequence[str] | None = None,
        created_from: str | None = None,
        created_to: str | None = None,
        starting_after: str | None = None,
        limit: int | None = None,
        timestamp: int | None = None,
    ) -> EventPage:
        """One page of events, newest first.

        ``timestamp`` (Unix time) signs the request and defaults to now - the API accepts +/- 300 s.
        """
        operation = ops.list_events(
            self._api.service,
            self._api.checksum,
            types=types,
            created_from=created_from,
            created_to=created_to,
            starting_after=starting_after,
            limit=limit,
            timestamp=timestamp,
        )
        return cast(EventPage, self._api.execute(operation))

    def iterate(
        self,
        *,
        types: Sequence[str] | None = None,
        created_from: str | None = None,
        created_to: str | None = None,
        starting_after: str | None = None,
        limit: int | None = None,
    ) -> Iterator[WebhookEvent]:
        """All matching events page by page, newest first."""
        while True:
            page = self.list(
                types=types,
                created_from=created_from,
                created_to=created_to,
                starting_after=starting_after,
                limit=limit,
            )
            yield from page.data
            starting_after = page.next_starting_after
            if not page.has_more or starting_after is None:
                return


class AsyncEventService:
    def __init__(self, api: AsyncApiRequestor) -> None:
        self._api = api

    async def list(
        self,
        *,
        types: Sequence[str] | None = None,
        created_from: str | None = None,
        created_to: str | None = None,
        starting_after: str | None = None,
        limit: int | None = None,
        timestamp: int | None = None,
    ) -> EventPage:
        operation = ops.list_events(
            self._api.service,
            self._api.checksum,
            types=types,
            created_from=created_from,
            created_to=created_to,
            starting_after=starting_after,
            limit=limit,
            timestamp=timestamp,
        )
        return cast(EventPage, await self._api.execute(operation))

    async def iterate(
        self,
        *,
        types: Sequence[str] | None = None,
        created_from: str | None = None,
        created_to: str | None = None,
        starting_after: str | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[WebhookEvent]:
        while True:
            page = await self.list(
                types=types,
                created_from=created_from,
                created_to=created_to,
                starting_after=starting_after,
                limit=limit,
            )
            for event in page.data:
                yield event
            starting_after = page.next_starting_after
            if not page.has_more or starting_after is None:
                return
