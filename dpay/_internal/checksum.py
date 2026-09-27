from __future__ import annotations

import hashlib
from collections.abc import Iterator, Mapping, Sequence
from typing import Any

from dpay._internal.php import is_scalar, php_strval


class ChecksumCalculator:
    def __init__(self, secret_hash: str) -> None:
        self._secret_hash = secret_hash

    def secret_second(self, service: str, fields: Sequence[Any]) -> str:
        """sha256(service|secret_hash|field1|field2|...) - registration, BLIK aliases, recurring, events."""
        parts = [service, self._secret_hash, *(php_strval(field) for field in fields)]
        return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()

    def ordered_body(self, body: Mapping[str, Any] | Sequence[Any]) -> str:
        """sha256(value1|value2|...|secret_hash) over the request body in the order it is sent.

        PBL API: refunds, transaction details, banks, payouts. The ``checksum`` key is skipped, nested
        objects (e.g. ``webhook``) contribute their leaf values in order, ``None`` and ``False`` give an
        empty segment and ``True`` gives ``1`` - the same way the API casts JSON values to strings.
        """
        items = body.items() if isinstance(body, Mapping) else enumerate(body)
        parts: list[str] = []
        for key, value in items:
            if key == "checksum":
                continue
            parts.extend(_segments(value))
        joined = "|".join(parts)
        return hashlib.sha256(f"{joined}|{self._secret_hash}".encode()).hexdigest()

    def operation(self, operation: str, service: str, transaction_id: str, amount: str | None) -> str:
        """sha256(operation|service|transaction_id|amount|secret_hash) - Cards API capture and cancellation.

        The operation name keeps a capture checksum from authorising a cancellation; without an amount
        the segment stays empty.
        """
        parts = [operation, service, transaction_id, "" if amount is None else amount, self._secret_hash]
        return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _segments(value: Any) -> Iterator[str]:
    if isinstance(value, Mapping):
        for item in value.values():
            yield from _segments(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _segments(item)
    else:
        yield php_strval(value) if is_scalar(value) else ""
