from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests import scenario

GOLDEN = json.loads((Path(__file__).parent / "golden" / "php_sdk_golden.json").read_text("utf-8"))
ACTUAL = scenario.run()


def _normalize(value: Any) -> Any:
    if isinstance(value, dict) and value and all(key.isdigit() for key in value):
        return [value[key] for key in sorted(value, key=int)]
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
    return {key: item for key, item in target.items() if "User-Agent" not in key}


GOLDEN_LEAVES = _leaves(GOLDEN)
ACTUAL_LEAVES = _leaves(ACTUAL)


def test_golden_covers_every_endpoint() -> None:
    assert len(GOLDEN["calls"]) == 23
    assert len(ACTUAL["calls"]) == len(GOLDEN["calls"])


def test_no_leaf_is_missing() -> None:
    assert set(ACTUAL_LEAVES) == set(GOLDEN_LEAVES)


@pytest.mark.parametrize("path", sorted(GOLDEN_LEAVES))
def test_matches_php_sdk(path: str) -> None:
    assert ACTUAL_LEAVES[path] == GOLDEN_LEAVES[path]


def test_user_agent_identifies_python_sdk() -> None:
    from dpay.version import SDK_VERSION

    agent = ACTUAL["calls"][0]["headers"]["User-Agent"]
    assert agent.startswith(f"dpay-python-sdk/{SDK_VERSION} python/")
