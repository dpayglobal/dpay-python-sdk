"""Reader of tests/fixtures/api_vectors.json - checksum and webhook vectors shared by all dpay SDKs.

The file is a byte-for-byte copy of the PHP SDK ``tests/Fixtures/api_vectors.json`` (synthetic data computed
with the API code - these are not dpay keys).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA: dict[str, Any] = json.loads(
    (Path(__file__).parent / "fixtures" / "api_vectors.json").read_text("utf-8")
)

SERVICE: str = DATA["service"]
SECRET_HASH: str = DATA["secret_hash"]
TRANSACTION_ID: str = DATA["transaction_id"]
SECRET_SECOND: list[dict[str, Any]] = DATA["secret_second"]
OPERATION: list[dict[str, Any]] = DATA["operation"]
ORDERED_BODY: list[dict[str, Any]] = DATA["ordered_body"]
WEBHOOK: dict[str, Any] = DATA["webhook"]


def vector(section: list[dict[str, Any]], name: str) -> dict[str, Any]:
    return next(item for item in section if item["name"] == name)
