from __future__ import annotations

import base64
import json

import pytest

from dpay import CardData, CardEncryptionError, CardEncryptor
from dpay._internal.php import php_json_encode
from dpay._internal.rsa import RsaError, load_public_key

PUBLIC_PEM_SPKI = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAqQLM5KwOZKy4iblKAkNn
f6qEJdENEUKu8Jpbi5ejrkLxwHWbwGUZcfQ8ciPSQv4boMJNxFSUziE4Z1+2VJpo
a75LPe8PQbB5bmlMkrcdvfsG72wE9NEufEA3JeQA26XO98qVC0cmTqVCkd1eFpC4
hPPabZDgEdhXd7olfhkR98RufW02LMgDfv1v73FBNHEAYlnkqSCgtCYteZbyEraA
pBh/LF1s24YUTxwCf4RlmtIgxxWqWssS4tlz9kL07ua2TM9E7L6RWokWbeEdxRyN
Sd6miCA0nl+Z0pXHtrlHrJNCgI0zzortdJQ6W6s3EVNnbZLSUWkqyN8zwWnaXVWl
EwIDAQAB
-----END PUBLIC KEY-----"""

PUBLIC_PEM_PKCS1 = """-----BEGIN RSA PUBLIC KEY-----
MIIBCgKCAQEAqQLM5KwOZKy4iblKAkNnf6qEJdENEUKu8Jpbi5ejrkLxwHWbwGUZ
cfQ8ciPSQv4boMJNxFSUziE4Z1+2VJpoa75LPe8PQbB5bmlMkrcdvfsG72wE9NEu
fEA3JeQA26XO98qVC0cmTqVCkd1eFpC4hPPabZDgEdhXd7olfhkR98RufW02LMgD
fv1v73FBNHEAYlnkqSCgtCYteZbyEraApBh/LF1s24YUTxwCf4RlmtIgxxWqWssS
4tlz9kL07ua2TM9E7L6RWokWbeEdxRyNSd6miCA0nl+Z0pXHtrlHrJNCgI0zzort
dJQ6W6s3EVNnbZLSUWkqyN8zwWnaXVWlEwIDAQAB
-----END RSA PUBLIC KEY-----"""

MODULUS = int(
    "2133565445034740737094001724065537847734120281793583159773142166982703"
    "2955069351064613696212045728469035379673510779788038197106000198315830"
    "2721001744621188755873690172376139325966781176452764433826140921856970"
    "6087286590391860910080693340831553088490844965186661881236573539829258"
    "5445205569982973137022356470470516544778183904473505984722011765510215"
    "1944714418710675964322649391703620014757873387530177662431419846253443"
    "2940571696638917277180214419251267548842255001659615263918452031246045"
    "2684362552134814106421606736485793005494334182093845024663112797114853"
    "585790119867834940879523045172767127736441790107879843091"
)

PUBLIC_EXPONENT = 65537

PRIVATE_EXPONENT = int(
    "1040038684598392699207197050196404132346032632596237258423067470415130"
    "7228216130711830168498500463667855917640869262887963383782373137854888"
    "5317116174609962573567553899887094664794860281125722345658844988793576"
    "7587325399442281161700229033363529403512779408621363308052929106869788"
    "4053557262984970975303312970577703684682225720249773713275033107647571"
    "2314321536104440153029809520030282503405249108504054697420829812013888"
    "1908145798097347167066941028800927875578562998289449004102136020843528"
    "8320462177333039106919296812494271034108420695849855700378977348573764"
    "104416636143877712219788427513475550308699495408696396825"
)

CARD = CardData("4111111111111111", "123", "12/28")


def _decrypt(ciphertext: bytes) -> bytes:
    block = pow(int.from_bytes(ciphertext, "big"), PRIVATE_EXPONENT, MODULUS)
    padded = block.to_bytes(256, "big")
    assert padded[0] == 0x00
    assert padded[1] == 0x02
    separator = padded.index(0x00, 2)
    assert separator >= 10
    assert 0x00 not in padded[2:separator]
    return padded[separator + 1 :]


def test_spki_and_pkcs1_describe_the_same_key() -> None:
    spki = load_public_key(PUBLIC_PEM_SPKI)
    pkcs1 = load_public_key(PUBLIC_PEM_PKCS1)
    assert spki.modulus == pkcs1.modulus == MODULUS
    assert spki.exponent == pkcs1.exponent == PUBLIC_EXPONENT
    assert spki.size_in_bytes == 256


def test_ciphertext_length_matches_key_size() -> None:
    encrypted = CardEncryptor().encrypt(CARD, "tx-1", PUBLIC_PEM_SPKI)
    assert len(base64.b64decode(encrypted, validate=True)) == 256


def test_ciphertext_is_randomized_per_call() -> None:
    encryptor = CardEncryptor()
    assert encryptor.encrypt(CARD, "tx-1", PUBLIC_PEM_SPKI) != encryptor.encrypt(
        CARD, "tx-1", PUBLIC_PEM_SPKI
    )


def test_round_trip_recovers_the_card_payload() -> None:
    encrypted = CardEncryptor().encrypt(CARD, "tx-42", PUBLIC_PEM_SPKI)
    payload = json.loads(_decrypt(base64.b64decode(encrypted)).decode("utf-8"))

    assert list(payload) == ["PN", "SC", "DT", "ID", "TX"]
    assert payload["PN"] == "4111111111111111"
    assert payload["SC"] == "123"
    assert payload["DT"] == "12/28"
    assert payload["ID"] == "tx-42"
    assert isinstance(payload["TX"], int)


def test_round_trip_works_with_pkcs1_key_too() -> None:
    encrypted = CardEncryptor().encrypt(CARD, "tx-1", PUBLIC_PEM_PKCS1)
    assert b'"PN":"4111111111111111"' in _decrypt(base64.b64decode(encrypted))


def test_payload_escapes_slashes_like_php() -> None:
    payload = php_json_encode(
        {"PN": CARD.pan, "SC": CARD.cvv, "DT": CARD.expiry, "ID": "tx-1", "TX": 1},
        escape_slashes=True,
    )
    assert payload == '{"PN":"4111111111111111","SC":"123","DT":"12\\/28","ID":"tx-1","TX":1}'


def test_encrypted_payload_carries_escaped_slash() -> None:
    encrypted = CardEncryptor().encrypt(CARD, "tx-1", PUBLIC_PEM_SPKI)
    assert b'"DT":"12\\/28"' in _decrypt(base64.b64decode(encrypted))


def test_invalid_pem_raises_card_encryption_error() -> None:
    with pytest.raises(CardEncryptionError, match="Invalid RSA public key"):
        CardEncryptor().encrypt(CARD, "tx-1", "not a key")


def test_truncated_pem_raises() -> None:
    with pytest.raises(RsaError):
        load_public_key("-----BEGIN PUBLIC KEY-----\nAAAA\n-----END PUBLIC KEY-----")


def test_unsupported_pem_label_raises() -> None:
    with pytest.raises(RsaError):
        load_public_key("-----BEGIN CERTIFICATE-----\nAAAA\n-----END CERTIFICATE-----")


def test_plaintext_too_long_raises() -> None:
    with pytest.raises(RsaError, match="Plaintext too long"):
        load_public_key(PUBLIC_PEM_SPKI).encrypt_pkcs1_v15(b"x" * 250)


def test_maximum_length_plaintext_is_accepted() -> None:
    key = load_public_key(PUBLIC_PEM_SPKI)
    plaintext = b"x" * (key.size_in_bytes - 11)
    assert _decrypt(key.encrypt_pkcs1_v15(plaintext)) == plaintext
