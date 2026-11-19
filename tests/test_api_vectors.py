"""Shared checksum vectors of all dpay SDKs (tests/fixtures/api_vectors.json)."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from typing import Any

import pytest

from dpay import DPayClient, IpnVerifier, PayoutState, SignatureVerificationError
from dpay._internal.checksum import ChecksumCalculator
from dpay._internal.server_trim import server_trim, trim_strings
from dpay.testing import MockHttpClient
from tests import api_vectors

CALCULATOR = ChecksumCalculator(api_vectors.SECRET_HASH)


def _names(section: list[dict[str, Any]]) -> list[str]:
    return [item["name"] for item in section]


def test_vectors_cover_every_checksum_kind() -> None:
    assert len(api_vectors.SECRET_SECOND) == 10
    assert len(api_vectors.OPERATION) == 4
    assert len(api_vectors.ORDERED_BODY) == 9
    assert len(api_vectors.IPN) == 3


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


def test_server_trim_vectors_are_complete() -> None:
    assert len(api_vectors.SERVER_TRIM_STRINGS) == 8
    assert len(api_vectors.SERVER_TRIM_BODIES) == 4


@pytest.mark.parametrize("name", _names(api_vectors.SERVER_TRIM_STRINGS))
def test_server_trim_string_vectors(name: str) -> None:
    item = api_vectors.vector(api_vectors.SERVER_TRIM_STRINGS, name)
    assert server_trim(item["input"]) == item["trimmed"]


@pytest.mark.parametrize("name", _names(api_vectors.SERVER_TRIM_BODIES))
def test_server_trim_body_vectors(name: str) -> None:
    item = api_vectors.vector(api_vectors.SERVER_TRIM_BODIES, name)
    body = trim_strings(item["input"])
    assert body == item["body"]
    assert list(body) == list(item["body"])
    assert CALCULATOR.ordered_body(body) == item["checksum"]
    assert CALCULATOR.ordered_body(item["input"]) != item["checksum"]


@pytest.mark.parametrize("name", _names(api_vectors.IPN))
def test_ipn_vectors(name: str) -> None:
    payload = api_vectors.vector(api_vectors.IPN, name)["payload"]
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    event = IpnVerifier.construct_event(body, api_vectors.SECRET_HASH)
    assert event.id == api_vectors.TRANSACTION_ID
    assert event.raw == payload

    with pytest.raises(SignatureVerificationError, match=r"^Invalid IPN signature$"):
        IpnVerifier.construct_event(body, api_vectors.SECRET_HASH + "x")


def test_ipn_alias_update_vector_is_typed() -> None:
    payload = api_vectors.vector(api_vectors.IPN, "alias_update_recurring_register")["payload"]
    event = IpnVerifier.construct_event(json.dumps(payload), api_vectors.SECRET_HASH)
    alias = event.alias_update
    assert alias is not None
    assert alias.change_type == "ALIAS_REGISTER"
    assert alias.alias_type == "PAYID"
    assert alias.is_active
    assert alias.alias_key == "BLIK-ALIAS-KEY-0001"
    assert alias.change_reason_category is None


_EMPTY_LIST = {"withdraws": [], "meta": {"page": 1, "per_page": 50, "total": 0, "total_pages": 0}}
_EMPTY_FULL: dict[str, Any] = {"settlement": {}, "summary": {}, "transactions": [], "meta": {}}

_PAYOUT_CALLS: dict[str, Callable[[DPayClient], object]] = {
    "payouts_list_minimal": lambda client: client.payouts.list(),
    "payouts_list_all_filters": lambda client: client.payouts.list(
        {"date_from": "2026-08-01", "date_to": "2026-08-31 23:59:59", "state": 1, "type": "standard"}, 2, 10
    ),
    "payouts_list_state_failed": lambda client: client.payouts.list({"state": PayoutState.FAILED}),
    "payouts_list_state_waiting_page_1": lambda client: client.payouts.list(
        {"state": PayoutState.WAITING}, 1
    ),
    "payouts_details_full_minimal": lambda client: client.payouts.details_full(12345),
    "payouts_details_full_page": lambda client: client.payouts.details_full(12345, 2, 500),
}


@pytest.mark.parametrize("name", sorted(_PAYOUT_CALLS))
def test_payout_bodies_match_the_shared_vectors(name: str) -> None:
    transport = MockHttpClient()
    client = DPayClient(
        service=api_vectors.SERVICE, secret_hash=api_vectors.SECRET_HASH, http_client=transport
    )
    transport.queue_json(200, _EMPTY_LIST if name.startswith("payouts_list") else _EMPTY_FULL)
    _PAYOUT_CALLS[name](client)

    body = transport.last_request_body
    checksum = body.pop("checksum")
    item = api_vectors.vector(api_vectors.ORDERED_BODY, name)
    assert list(body.items()) == list(item["body"].items())
    assert checksum == item["checksum"]


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
