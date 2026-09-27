"""Shared checksum vectors of all dpay SDKs (tests/fixtures/api_vectors.json)."""

from __future__ import annotations

import hashlib
from typing import Any

import pytest

from dpay._internal.checksum import ChecksumCalculator
from tests import api_vectors

CALCULATOR = ChecksumCalculator(api_vectors.SECRET_HASH)


def _names(section: list[dict[str, Any]]) -> list[str]:
    return [item["name"] for item in section]


def test_vectors_cover_every_checksum_kind() -> None:
    assert len(api_vectors.SECRET_SECOND) == 10
    assert len(api_vectors.OPERATION) == 4
    assert len(api_vectors.ORDERED_BODY) == 3


@pytest.mark.parametrize("name", _names(api_vectors.SECRET_SECOND))
def test_secret_second_vectors(name: str) -> None:
    item = api_vectors.vector(api_vectors.SECRET_SECOND, name)
    assert CALCULATOR.secret_second(api_vectors.SERVICE, item["fields"]) == item["checksum"]


@pytest.mark.parametrize("name", _names(api_vectors.OPERATION))
def test_operation_vectors(name: str) -> None:
    item = api_vectors.vector(api_vectors.OPERATION, name)
    checksum = CALCULATOR.operation(
        item["operation"], api_vectors.SERVICE, api_vectors.TRANSACTION_ID, item["amount"]
    )
    assert checksum == item["checksum"]


@pytest.mark.parametrize("name", _names(api_vectors.ORDERED_BODY))
def test_ordered_body_vectors(name: str) -> None:
    item = api_vectors.vector(api_vectors.ORDERED_BODY, name)
    assert CALCULATOR.ordered_body(item["body"]) == item["checksum"]


def test_ordered_body_skips_checksum_and_casts_like_the_api() -> None:
    calculator = ChecksumCalculator("h")
    body = {"x": "a", "checksum": "ignored", "y": True, "z": None, "w": {"v": "b"}}
    assert calculator.ordered_body(body) == hashlib.sha256(b"a|1||b|h").hexdigest()


def test_ordered_body_flattens_lists_and_nested_objects_in_order() -> None:
    calculator = ChecksumCalculator("h")
    body = {"a": [1, {"b": False, "c": [2.5, "x"]}], "d": [], "e": 10.0}
    assert calculator.ordered_body(body) == hashlib.sha256(b"1||2.5|x|10|h").hexdigest()


def test_ordered_body_of_an_empty_body_is_the_hash_after_a_separator() -> None:
    assert ChecksumCalculator("h").ordered_body({}) == hashlib.sha256(b"|h").hexdigest()


def test_ordered_body_still_accepts_plain_values() -> None:
    calculator = ChecksumCalculator("h")
    assert calculator.ordered_body(["s", 5]) == calculator.ordered_body({"service": "s", "id": 5})


def test_operation_without_amount_keeps_the_empty_segment() -> None:
    checksum = ChecksumCalculator("h").operation("cancellation", "s", "tx", None)
    assert checksum == hashlib.sha256(b"cancellation|s|tx||h").hexdigest()
