from __future__ import annotations

import hashlib
import json

import pytest

from dpay import IpnEvent, IpnType, IpnVerifier, SignatureVerificationError
from tests.conftest import SECRET
from tests.scenario import ipn_signature

BASE = {
    "id": "tx-1",
    "amount": "29.99",
    "email": "jan@example.com",
    "type": "transfer",
    "attempt": 1,
    "version": 2,
    "custom": "order-1",
}


def _signed(payload: dict[str, object]) -> str:
    return json.dumps({**payload, "signature": ipn_signature(payload)})


def test_ack_is_literal_ok() -> None:
    assert IpnEvent.ACK == "OK"


def test_transfer_signature_is_accepted() -> None:
    event = IpnVerifier.construct_event(_signed(BASE), SECRET)
    assert event.is_transfer
    assert event.id == "tx-1"
    assert event.amount == "29.99"
    assert event.email == "jan@example.com"
    assert event.attempt == 1
    assert event.version == 2
    assert event.custom == "order-1"


def test_capture_exposes_capture_payment_id() -> None:
    payload = {**BASE, "type": "capture", "capture_payment_id": "cap-9"}
    event = IpnVerifier.construct_event(_signed(payload), SECRET)
    assert event.is_capture
    assert event.capture_payment_id == "cap-9"


def test_dcb_signature_omits_email() -> None:
    payload = {"id": "tx-2", "amount": "10.50", "type": "dcb", "attempt": 3, "version": 1}
    event = IpnVerifier.construct_event(_signed(payload), SECRET)
    assert event.is_dcb
    assert event.email is None


def test_dcb_signature_ignores_a_present_email() -> None:
    payload = {
        "id": "tx-2",
        "amount": "10.50",
        "email": "jan@example.com",
        "type": "dcb",
        "attempt": 3,
        "version": 1,
    }
    without_email_slot = hashlib.sha256(f"tx-2{SECRET}10.50dcb31".encode()).hexdigest()
    with_email_slot = hashlib.sha256(f"tx-2{SECRET}10.50jan@example.comdcb31".encode()).hexdigest()

    assert ipn_signature(payload) == without_email_slot
    assert ipn_signature(payload) != with_email_slot
    assert IpnVerifier.construct_event(_signed(payload), SECRET).is_dcb


def test_missing_email_hashes_as_empty_string() -> None:
    payload = {"id": "tx-1", "amount": "1.00", "type": "transfer", "attempt": 1, "version": 1}
    event = IpnVerifier.construct_event(_signed(payload), SECRET)
    assert event.email is None
    assert event.custom is None


def test_amount_is_never_normalized() -> None:
    payload = {**BASE, "amount": "10.5"}
    assert IpnVerifier.construct_event(_signed(payload), SECRET).amount == "10.5"


def test_numeric_amount_uses_php_string_cast() -> None:
    payload = {**BASE, "amount": 10.0}
    event = IpnVerifier.construct_event(_signed(payload), SECRET)
    assert event.amount == "10"


def test_bad_signature_is_rejected() -> None:
    body = json.dumps({**BASE, "signature": "0" * 64})
    with pytest.raises(SignatureVerificationError, match="Invalid IPN signature"):
        IpnVerifier.construct_event(body, SECRET)


def test_wrong_secret_is_rejected() -> None:
    with pytest.raises(SignatureVerificationError, match="Invalid IPN signature"):
        IpnVerifier.construct_event(_signed(BASE), "inny-sekret")


def test_tampered_amount_is_rejected() -> None:
    payload = json.loads(_signed(BASE))
    payload["amount"] = "1.00"
    with pytest.raises(SignatureVerificationError, match="Invalid IPN signature"):
        IpnVerifier.construct_event(json.dumps(payload), SECRET)


def test_malformed_json_is_rejected() -> None:
    with pytest.raises(SignatureVerificationError, match="Invalid IPN payload"):
        IpnVerifier.construct_event("not json", SECRET)


def test_non_object_payload_is_rejected() -> None:
    with pytest.raises(SignatureVerificationError, match="Invalid IPN payload"):
        IpnVerifier.construct_event("[1,2]", SECRET)


@pytest.mark.parametrize("field", ["id", "amount", "type", "attempt", "version", "signature"])
def test_missing_required_field_is_rejected(field: str) -> None:
    payload = json.loads(_signed(BASE))
    del payload[field]
    with pytest.raises(SignatureVerificationError, match="Invalid IPN payload"):
        IpnVerifier.construct_event(json.dumps(payload), SECRET)


def test_null_required_field_is_rejected() -> None:
    payload = json.loads(_signed(BASE))
    payload["amount"] = None
    with pytest.raises(SignatureVerificationError, match="Invalid IPN payload"):
        IpnVerifier.construct_event(json.dumps(payload), SECRET)


def test_non_string_signature_is_rejected() -> None:
    payload = json.loads(_signed(BASE))
    payload["signature"] = 123
    with pytest.raises(SignatureVerificationError, match="Invalid IPN payload"):
        IpnVerifier.construct_event(json.dumps(payload), SECRET)


def test_bytes_body_is_accepted() -> None:
    event = IpnVerifier.construct_event(_signed(BASE).encode("utf-8"), SECRET)
    assert event.id == "tx-1"


def test_raw_payload_is_available() -> None:
    event = IpnVerifier.construct_event(_signed(BASE), SECRET)
    assert event.raw["custom"] == "order-1"


def test_ipn_type_validation() -> None:
    IpnType.assert_valid(IpnType.TRANSFER)
    with pytest.raises(Exception, match='Invalid IPN type "nope"'):
        IpnType.assert_valid("nope")
