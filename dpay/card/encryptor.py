from __future__ import annotations

import base64
import time

from dpay._internal.php import php_json_encode
from dpay._internal.rsa import RsaError, load_public_key
from dpay.card.card_data import CardData
from dpay.exceptions import CardEncryptionError


class CardEncryptor:
    def encrypt(self, card: CardData, transaction_id: str, public_key_pem: str) -> str:
        try:
            key = load_public_key(public_key_pem)
        except RsaError as error:
            raise CardEncryptionError("Invalid RSA public key") from error

        payload = php_json_encode(
            {
                "PN": card.pan,
                "SC": card.cvv,
                "DT": card.expiry,
                "ID": transaction_id,
                "TX": int(time.time()),
            },
            escape_slashes=True,
        )

        try:
            encrypted = key.encrypt_pkcs1_v15(payload.encode("utf-8"))
        except RsaError as error:
            raise CardEncryptionError("Card data encryption failed") from error

        return base64.b64encode(encrypted).decode("ascii")
