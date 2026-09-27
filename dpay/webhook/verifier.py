from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import time
from collections.abc import Iterable, Sequence
from typing import Any, Protocol

from dpay.exceptions import DPayValueError, SignatureVerificationError
from dpay.webhook.event import WebhookEvent

_TIMESTAMP = re.compile(r"[0-9]+")
# PHP: preg_split('/\s+/', trim($header)) - PCRE \s without /u and the characters trim() removes
_SIGNATURE_SEPARATOR = re.compile(r"[ \t\n\x0b\f\r]+")
_TRIMMED = " \t\n\r\x00\x0b"
_SECRET_PREFIX = "whsec_"
_BASE64_ALPHABET = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/")
_BASE64_WHITESPACE = frozenset(" \t\n\r")
_MAX_TIMESTAMP_DIGITS = 18


class _Headers(Protocol):
    def items(self) -> Iterable[tuple[Any, Any]]: ...


class WebhookVerifier:
    """Verifies dpay webhooks (Standard Webhooks).

    ``webhook-signature`` = ``v1,`` + base64(HMAC-SHA256(key, id.timestamp.body)), where the key is the
    base64-decoded secret without the ``whsec_`` prefix. During a secret rotation dpay sends two
    signatures separated by a space - one match is enough.
    """

    DEFAULT_TOLERANCE = 300

    @staticmethod
    def construct_event(
        raw_body: str | bytes,
        headers: _Headers,
        secrets: str | Sequence[str],
        tolerance_seconds: int = DEFAULT_TOLERANCE,
        now: int | None = None,
    ) -> WebhookEvent:
        """Verifies the signature and returns the event.

        Pass the raw request body exactly as received (``bytes`` preferably) and the request headers as
        any mapping - names are matched without regard to letter case, a list value counts by its first
        item. ``secrets`` is the ``whsec_...`` secret of the endpoint, or several during a rotation.
        """
        WebhookVerifier.verify(raw_body, headers, secrets, tolerance_seconds, now)
        try:
            payload = json.loads(raw_body)
        except ValueError as error:
            raise SignatureVerificationError("Invalid webhook payload") from error
        if not isinstance(payload, dict):
            raise SignatureVerificationError("Invalid webhook payload")
        return WebhookEvent.from_api(payload)

    @staticmethod
    def verify(
        raw_body: str | bytes,
        headers: _Headers,
        secrets: str | Sequence[str],
        tolerance_seconds: int = DEFAULT_TOLERANCE,
        now: int | None = None,
    ) -> None:
        webhook_id = _header(headers, "webhook-id")
        timestamp = _header(headers, "webhook-timestamp")
        signature_header = _header(headers, "webhook-signature")
        if webhook_id is None or timestamp is None or signature_header is None:
            raise SignatureVerificationError(
                "Missing webhook-id, webhook-timestamp or webhook-signature header"
            )
        if _TIMESTAMP.fullmatch(timestamp) is None:
            raise SignatureVerificationError("Invalid webhook-timestamp header")
        current = int(time.time()) if now is None else now
        if len(timestamp) > _MAX_TIMESTAMP_DIGITS or abs(current - int(timestamp)) > tolerance_seconds:
            raise SignatureVerificationError("Webhook timestamp is outside the tolerance zone")

        body = _bytes(raw_body) if isinstance(raw_body, str) else bytes(raw_body)
        signed = _bytes(f"{webhook_id}.{timestamp}.") + body
        expected = [
            base64.b64encode(hmac.new(_key(secret), signed, hashlib.sha256).digest())
            for secret in _secret_list(secrets)
        ]

        for entry in _SIGNATURE_SEPARATOR.split(signature_header.strip(_TRIMMED)):
            version, separator, signature = entry.partition(",")
            if separator == "" or version != "v1":
                continue
            candidate = _bytes(signature)
            for value in expected:
                if hmac.compare_digest(value, candidate):
                    return

        raise SignatureVerificationError("No valid webhook signature found")


def _header(headers: _Headers, name: str) -> str | None:
    for key, value in headers.items():
        text_key = _text(key)
        if text_key is None or not text_key.isascii() or text_key.lower() != name:
            continue
        if isinstance(value, (list, tuple)):
            value = value[0] if value else None
        text = _text(value)
        return text if text else None
    return None


def _text(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("latin-1")
    return None


def _bytes(text: str) -> bytes:
    return text.encode("utf-8", "surrogatepass")


def _secret_list(secrets: str | Sequence[str]) -> list[Any]:
    return [secrets] if isinstance(secrets, str) else list(secrets)


def _key(secret: Any) -> bytes:
    if isinstance(secret, str):
        encoded = secret[len(_SECRET_PREFIX) :] if secret.startswith(_SECRET_PREFIX) else secret
        key = _decode_base64(encoded)
        if key:
            return key
    raise DPayValueError("Webhook secret must be the whsec_ value from the dpay panel")


def _decode_base64(text: str) -> bytes | None:
    # PHP base64_decode($text, true): whitespace is skipped, padding may be missing, anything else fails
    data: list[str] = []
    padding = 0
    for character in text:
        if character == "=":
            padding += 1
        elif character in _BASE64_WHITESPACE:
            continue
        elif character not in _BASE64_ALPHABET or padding:
            return None
        else:
            data.append(character)
    if len(data) % 4 == 1 or (padding and (padding > 2 or (len(data) + padding) % 4 != 0)):
        return None
    joined = "".join(data)
    return base64.b64decode(joined + "=" * (-len(joined) % 4))
