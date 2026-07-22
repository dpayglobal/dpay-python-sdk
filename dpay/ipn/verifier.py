from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from dpay._internal.php import is_numeric, is_scalar, php_strval
from dpay.exceptions import SignatureVerificationError
from dpay.ipn.event import IpnEvent, IpnType

_REQUIRED = ("id", "amount", "type", "attempt", "version", "signature")


class IpnVerifier:
    @staticmethod
    def construct_event(raw_body: str | bytes, secret_hash: str) -> IpnEvent:
        if isinstance(raw_body, bytes):
            raw_body = raw_body.decode("utf-8", "replace")
        try:
            payload = json.loads(raw_body)
        except ValueError as error:
            raise SignatureVerificationError("Invalid IPN payload") from error
        if not isinstance(payload, dict):
            raise SignatureVerificationError("Invalid IPN payload")

        for field in _REQUIRED:
            if payload.get(field) is None:
                raise SignatureVerificationError("Invalid IPN payload")

        signature = payload["signature"]
        if not isinstance(signature, str):
            raise SignatureVerificationError("Invalid IPN payload")

        expected = _expected_signature(payload, secret_hash)
        if not hmac.compare_digest(expected, signature):
            raise SignatureVerificationError("Invalid IPN signature")

        return IpnEvent(payload)


def _expected_signature(payload: dict[str, Any], secret_hash: str) -> str:
    type_ = php_strval(payload["type"]) if is_scalar(payload["type"]) else ""
    id_ = php_strval(payload["id"]) if is_scalar(payload["id"]) else ""
    amount = php_strval(payload["amount"]) if is_scalar(payload["amount"]) else ""
    email = payload.get("email")
    email = php_strval(email) if is_scalar(email) else ""
    attempt = php_strval(payload["attempt"]) if is_numeric(payload["attempt"]) else "0"
    version = php_strval(payload["version"]) if is_numeric(payload["version"]) else "0"
    custom = payload.get("custom")
    custom = php_strval(custom) if is_scalar(custom) else ""

    parts = [id_, secret_hash, amount]
    if type_ != IpnType.DCB:
        parts.append(email)
    parts.extend([type_, attempt, version, custom])

    return hashlib.sha256("".join(parts).encode("utf-8")).hexdigest()
