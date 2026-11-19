from __future__ import annotations

import hashlib
import json

import pytest

from dpay import AliasUpdate, IpnEvent, IpnType, IpnVerifier, SignatureVerificationError
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


# alias_update (0.3.0) - signed as sha256(id + secret_hash + type + version)

ALIAS_ID = "30D9493D-1D73-3FBD-A5D4-633723CC7A68"


def _alias_update(**overrides: object) -> str:
    payload: dict[str, object] = {
        "id": ALIAS_ID,
        "type": "alias_update",
        "change_type": "ALIAS_UNREGISTER",
        "alias_type": "UID",
        "alias_status": "UNREGISTERED",
        "alias_label": "Moj sklep",
        "alias_key": "KEY-1",
        "alias_expire_at": None,
        "change_reason_category": "USER",
        "change_reason_message": "Unregistered in the banking app",
        "version": 1,
    }
    payload.update(overrides)
    payload.setdefault("signature", hashlib.sha256(f"{ALIAS_ID}{SECRET}alias_update1".encode()).hexdigest())
    return json.dumps(payload)


def test_alias_update_type() -> None:
    assert IpnType.ALIAS_UPDATE == "alias_update"
    assert IpnType.ALL == ("transfer", "capture", "dcb", "alias_update")
    IpnType.assert_valid(IpnType.ALIAS_UPDATE)


def test_valid_alias_update() -> None:
    event = IpnVerifier.construct_event(_alias_update(), SECRET)

    assert event.is_alias_update
    assert not event.is_transfer
    assert event.amount == ""
    assert event.id == ALIAS_ID
    alias = event.alias_update
    assert alias is not None
    assert alias.change_type == AliasUpdate.CHANGE_UNREGISTER
    assert alias.alias_type == AliasUpdate.ALIAS_TYPE_UID
    assert alias.alias_status == AliasUpdate.STATUS_UNREGISTERED
    assert not alias.is_active
    assert alias.alias_key == "KEY-1"
    assert alias.alias_label == "Moj sklep"
    assert alias.alias_expire_at is None
    assert alias.change_reason_category == "USER"
    assert alias.change_reason_message == "Unregistered in the banking app"


def test_alias_update_signature_ignores_the_alias_fields() -> None:
    # The signature covers only id, type and version - a changed status still verifies, a changed id does not
    event = IpnVerifier.construct_event(_alias_update(alias_status="ACTIVE"), SECRET)
    alias = event.alias_update
    assert alias is not None
    assert alias.is_active

    with pytest.raises(SignatureVerificationError, match=r"^Invalid IPN signature$"):
        IpnVerifier.construct_event(_alias_update(id="OTHER"), SECRET)


def test_alias_update_without_version_is_invalid() -> None:
    with pytest.raises(SignatureVerificationError, match=r"^Invalid IPN payload$"):
        IpnVerifier.construct_event(_alias_update(version=None), SECRET)


def test_alias_update_needs_neither_amount_nor_attempt() -> None:
    payload = json.loads(_alias_update())
    assert "amount" not in payload
    assert "attempt" not in payload
    assert IpnVerifier.construct_event(json.dumps(payload), SECRET).is_alias_update


def test_alias_update_ignores_unsigned_transfer_fields() -> None:
    # amount, email, attempt and custom are not part of the alias_update signature - an injected value
    # must not reach handlers that read them without checking the type
    event = IpnVerifier.construct_event(
        _alias_update(amount="999.00", email="attacker@example.com", attempt=7, custom="order-1234"), SECRET
    )

    assert event.is_alias_update
    assert event.amount == ""
    assert event.email is None
    assert event.attempt == 0
    assert event.custom is None
    assert event.id == ALIAS_ID
    assert event.version == 1
    # The raw payload still holds everything that was sent
    assert event.raw["amount"] == "999.00"


def test_transfer_signature_does_not_verify_as_alias_update() -> None:
    payload = json.loads(_signed(BASE))
    payload["type"] = "alias_update"
    with pytest.raises(SignatureVerificationError, match=r"^Invalid IPN signature$"):
        IpnVerifier.construct_event(json.dumps(payload), SECRET)


def test_alias_update_signature_does_not_verify_as_transfer() -> None:
    with pytest.raises(SignatureVerificationError, match=r"^Invalid IPN signature$"):
        IpnVerifier.construct_event(_alias_update(type="transfer", amount="", attempt=1), SECRET)


def test_transfer_has_no_alias_update() -> None:
    event = IpnVerifier.construct_event(_signed(BASE), SECRET)
    assert not event.is_alias_update
    assert event.alias_update is None
