from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ApiRequest:
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    body: str | None = None


class ApiResponse:
    def __init__(self, status: int, headers: Mapping[str, str], body: str) -> None:
        self.status = status
        self.headers = {name.lower(): value for name, value in headers.items()}
        self.body = body

    def get_header(self, name: str) -> str | None:
        return self.headers.get(name.lower())

    def decode_json(self) -> Any:
        try:
            decoded = json.loads(self.body)
        except ValueError:
            return None
        return decoded if isinstance(decoded, (dict, list)) else None
