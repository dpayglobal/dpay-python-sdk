from __future__ import annotations

from typing import Any

import pytest

from dpay import DPayValueError, SignatureVerificationError, WebhookVerifier
from tests import api_vectors

VECTOR = api_vectors.WEBHOOK
BODY: str = VECTOR["body"]
SECRET: str = VECTOR["secret"]
TIMESTAMP: int = VECTOR["timestamp"]


def _headers(signature: str | None = None) -> dict[str, Any]:
    return {
        "Webhook-Id": VECTOR["id"],
        "WEBHOOK-TIMESTAMP": str(TIMESTAMP),
        "webhook-signature": VECTOR["signature"] if signature is None else signature,
    }


def test_verifies_the_signature_and_returns_the_event() -> None:
    event = WebhookVerifier.construct_event(BODY, _headers(), SECRET, 300, TIMESTAMP + 10)

    assert event.id == VECTOR["id"]
    assert event.type == "payment.succeeded"
    assert event.object_type == "payment"
    assert event.object["amount"] == 1000


def test_accepts_the_raw_body_as_bytes() -> None:
    event = WebhookVerifier.construct_event(BODY.encode("utf-8"), _headers(), SECRET, now=TIMESTAMP)
    assert event.id == VECTOR["id"]


def test_accepts_headers_as_lists_and_the_secret_without_prefix() -> None:
    headers = {name: [value] for name, value in _headers().items()}
    WebhookVerifier.verify(BODY, headers, SECRET.removeprefix("whsec_"), 300, TIMESTAMP)


def test_accepts_byte_headers_of_raw_asgi_scopes() -> None:
    headers = {name.lower().encode(): value.encode() for name, value in _headers().items()}
    WebhookVerifier.verify(BODY, headers, SECRET, 300, TIMESTAMP)


def test_accepts_either_signature_during_a_rotation() -> None:
    # Only the old secret on the receiver's side, the header carries both signatures
    WebhookVerifier.verify(BODY, _headers(VECTOR["rotation_signature"]), VECTOR["old_secret"], 300, TIMESTAMP)
    # Both secrets on the receiver's side
    WebhookVerifier.verify(BODY, _headers(), [VECTOR["old_secret"], SECRET], 300, TIMESTAMP)


def test_rejects_a_tampered_body() -> None:
    with pytest.raises(SignatureVerificationError, match="No valid webhook signature found"):
        WebhookVerifier.verify(BODY.replace("1000", "100000"), _headers(), SECRET, 300, TIMESTAMP)


@pytest.mark.parametrize("delta", [301, -301])
def test_rejects_a_timestamp_outside_the_tolerance(delta: int) -> None:
    with pytest.raises(SignatureVerificationError, match="tolerance"):
        WebhookVerifier.verify(BODY, _headers(), SECRET, 300, TIMESTAMP + delta)


def test_accepts_the_edge_of_the_tolerance() -> None:
    WebhookVerifier.verify(BODY, _headers(), SECRET, 300, TIMESTAMP + 300)
    WebhookVerifier.verify(BODY, _headers(), SECRET, 300, TIMESTAMP - 300)


@pytest.mark.parametrize("missing", ["Webhook-Id", "WEBHOOK-TIMESTAMP", "webhook-signature"])
def test_rejects_missing_headers(missing: str) -> None:
    headers = _headers()
    del headers[missing]
    with pytest.raises(SignatureVerificationError, match="Missing webhook-id"):
        WebhookVerifier.verify(BODY, headers, SECRET, 300, TIMESTAMP)


def test_an_empty_header_counts_as_missing() -> None:
    headers = {**_headers(), "webhook-signature": ""}
    with pytest.raises(SignatureVerificationError, match="Missing webhook-id"):
        WebhookVerifier.verify(BODY, headers, SECRET, 300, TIMESTAMP)


@pytest.mark.parametrize(
    "timestamp",
    [
        "1790503500.5",
        "-1790503500",
        "abc",
        " 1790503500",
        "\uff11\uff17\uff19\uff10\uff15\uff10\uff13\uff15\uff10\uff10",
    ],
)
def test_rejects_a_timestamp_that_is_not_digits(timestamp: str) -> None:
    headers = {**_headers(), "WEBHOOK-TIMESTAMP": timestamp}
    with pytest.raises(SignatureVerificationError, match="Invalid webhook-timestamp header"):
        WebhookVerifier.verify(BODY, headers, SECRET, 300, TIMESTAMP)


def test_a_huge_timestamp_is_outside_the_tolerance() -> None:
    headers = {**_headers(), "WEBHOOK-TIMESTAMP": "9" * 5000}
    with pytest.raises(SignatureVerificationError, match="tolerance"):
        WebhookVerifier.verify(BODY, headers, SECRET, 300, TIMESTAMP)


def test_ignores_signatures_of_other_versions() -> None:
    v2 = "v2," + VECTOR["signature"][3:]
    with pytest.raises(SignatureVerificationError, match="No valid webhook signature found"):
        WebhookVerifier.verify(BODY, _headers(v2), SECRET, 300, TIMESTAMP)


def test_finds_the_valid_entry_among_others() -> None:
    header = f"  v2,abc  v1,bm90LWl0\tv1  {VECTOR['signature']} "
    WebhookVerifier.verify(BODY, _headers(header), SECRET, 300, TIMESTAMP)


def test_a_non_ascii_signature_is_just_invalid() -> None:
    with pytest.raises(SignatureVerificationError, match="No valid webhook signature found"):
        WebhookVerifier.verify(BODY, _headers("v1,zażółć"), SECRET, 300, TIMESTAMP)


def test_rejects_the_wrong_secret() -> None:
    with pytest.raises(SignatureVerificationError, match="No valid webhook signature found"):
        WebhookVerifier.verify(BODY, _headers(), VECTOR["old_secret"], 300, TIMESTAMP)


@pytest.mark.parametrize(
    "secret", ["whsec_***", "whsec_", "", "whsec_ZHBheS1z=ZGst", "whsec_A", "whsec_QQ==="]
)
def test_a_secret_that_is_not_base64_is_a_configuration_error(secret: str) -> None:
    with pytest.raises(DPayValueError, match="whsec_ value from the dpay panel"):
        WebhookVerifier.verify(BODY, _headers(), secret, 300, TIMESTAMP)


def test_secret_decoding_tolerates_missing_padding_and_whitespace_like_php() -> None:
    unpadded = SECRET.rstrip("=") + "\n"
    WebhookVerifier.verify(BODY, _headers(), unpadded, 300, TIMESTAMP)


def test_construct_event_rejects_a_payload_that_is_not_an_object() -> None:
    import base64
    import hashlib
    import hmac

    body = "[1,2]"
    key = base64.b64decode(SECRET.removeprefix("whsec_"))
    signed = f"{VECTOR['id']}.{TIMESTAMP}.{body}".encode()
    signature = "v1," + base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()

    WebhookVerifier.verify(body, _headers(signature), SECRET, 300, TIMESTAMP)
    with pytest.raises(SignatureVerificationError, match="Invalid webhook payload"):
        WebhookVerifier.construct_event(body, _headers(signature), SECRET, 300, TIMESTAMP)


def test_official_standard_webhooks_vector() -> None:
    # Test vector of the Standard Webhooks specification (public data, not a dpay secret)
    headers = {
        "webhook-id": "msg_p5jXN8AQM9LWM0D4loKWxJek",
        "webhook-timestamp": "1614265330",
        "webhook-signature": "v1,g0hM9SsE+OTPJTGt/tmIKtSyZlE3uFJELVlNIOLJ1OE=",
    }
    event = WebhookVerifier.construct_event(
        b'{"test": 2432232314}', headers, "whsec_MfKQ9r8GKYqrTwjUPD8ILPZIo2LaLaSw", now=1614265330
    )
    assert event.raw == {"test": 2432232314}
    assert event.id == ""
