from __future__ import annotations

import hashlib
from collections.abc import Sequence
from typing import Any

from dpay._internal.php import php_strval


class ChecksumCalculator:
    def __init__(self, secret_hash: str) -> None:
        self._secret_hash = secret_hash

    def secret_second(self, service: str, fields: Sequence[Any]) -> str:
        parts = [service, self._secret_hash, *(php_strval(field) for field in fields)]
        return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()

    def ordered_body(self, values: Sequence[Any]) -> str:
        joined = "|".join(php_strval(value) for value in values)
        return hashlib.sha256(f"{joined}|{self._secret_hash}".encode()).hexdigest()
