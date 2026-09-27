from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests import response_scenario

GOLDEN = json.loads((Path(__file__).parent / "golden" / "php_response_golden.json").read_text("utf-8"))
ACTUAL = response_scenario.run()


def _normalize(value: Any) -> Any:
    if isinstance(value, dict) and value and all(key.isdigit() for key in value):
        return [value[key] for key in sorted(value, key=int)]
    if value == []:
        return {}
    return value


def _flatten(prefix: str, value: Any, target: dict[str, Any]) -> None:
    value = _normalize(value)
    if isinstance(value, dict):
        for key, item in value.items():
            _flatten(f"{prefix}.{key}", item, target)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _flatten(f"{prefix}[{index}]", item, target)
    else:
        target[prefix] = value


def _leaves(payload: dict[str, Any]) -> dict[str, Any]:
    target: dict[str, Any] = {}
    _flatten("", payload, target)
    return target


GOLDEN_LEAVES = _leaves(GOLDEN)
ACTUAL_LEAVES = _leaves(ACTUAL)


def test_every_model_group_is_covered() -> None:
    assert set(GOLDEN) == set(ACTUAL)
    assert set(GOLDEN) == {
        "registered",
        "transaction",
        "bank",
        "refund",
        "availability",
        "payout",
        "blik_alias",
        "card_result",
        "recurring_status",
        "recurring_retry",
        "webhook_event",
    }


def test_no_leaf_is_missing() -> None:
    assert set(ACTUAL_LEAVES) == set(GOLDEN_LEAVES)


@pytest.mark.parametrize("path", sorted(GOLDEN_LEAVES))
def test_parsing_matches_php_sdk(path: str) -> None:
    assert ACTUAL_LEAVES[path] == GOLDEN_LEAVES[path]
