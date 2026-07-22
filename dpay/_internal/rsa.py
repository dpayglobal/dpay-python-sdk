from __future__ import annotations

import base64
import re
import secrets

_PEM = re.compile(
    r"-----BEGIN (?P<label>[A-Z ]+)-----(?P<body>.*?)-----END (?P=label)-----",
    re.DOTALL,
)

_RSA_ENCRYPTION_OID = bytes.fromhex("06092a864886f70d010101")


class RsaError(ValueError):
    pass


class RsaPublicKey:
    def __init__(self, modulus: int, exponent: int) -> None:
        if modulus <= 0 or exponent <= 0:
            raise RsaError("Invalid RSA public key")
        self.modulus = modulus
        self.exponent = exponent

    @property
    def size_in_bytes(self) -> int:
        return (self.modulus.bit_length() + 7) // 8

    def encrypt_pkcs1_v15(self, plaintext: bytes) -> bytes:
        key_size = self.size_in_bytes
        if len(plaintext) > key_size - 11:
            raise RsaError("Plaintext too long for RSA key size")
        padding_length = key_size - len(plaintext) - 3
        padding = bytearray()
        while len(padding) < padding_length:
            candidate = secrets.token_bytes(padding_length - len(padding))
            padding.extend(byte for byte in candidate if byte != 0)
        block = b"\x00\x02" + bytes(padding[:padding_length]) + b"\x00" + plaintext
        cipher = pow(int.from_bytes(block, "big"), self.exponent, self.modulus)
        return cipher.to_bytes(key_size, "big")


def load_public_key(pem: str) -> RsaPublicKey:
    match = _PEM.search(pem)
    if match is None:
        raise RsaError("Invalid RSA public key")
    label = match.group("label").strip()
    try:
        der = base64.b64decode("".join(match.group("body").split()), validate=True)
    except ValueError as error:
        raise RsaError("Invalid RSA public key") from error

    if label == "RSA PUBLIC KEY":
        return _parse_pkcs1(der)
    if label == "PUBLIC KEY":
        return _parse_spki(der)
    raise RsaError("Invalid RSA public key")


def _parse_spki(der: bytes) -> RsaPublicKey:
    body = _read_sequence(der)
    algorithm, rest = _read_element(body)
    if _RSA_ENCRYPTION_OID not in algorithm.raw:
        raise RsaError("Invalid RSA public key")
    bitstring, _ = _read_element(rest)
    if bitstring.tag != 0x03 or not bitstring.content.startswith(b"\x00"):
        raise RsaError("Invalid RSA public key")
    return _parse_pkcs1(bitstring.content[1:])


def _parse_pkcs1(der: bytes) -> RsaPublicKey:
    body = _read_sequence(der)
    modulus, rest = _read_element(body)
    exponent, _ = _read_element(rest)
    if modulus.tag != 0x02 or exponent.tag != 0x02:
        raise RsaError("Invalid RSA public key")
    return RsaPublicKey(
        int.from_bytes(modulus.content, "big"),
        int.from_bytes(exponent.content, "big"),
    )


class _Element:
    def __init__(self, tag: int, content: bytes, raw: bytes) -> None:
        self.tag = tag
        self.content = content
        self.raw = raw


def _read_sequence(der: bytes) -> bytes:
    element, _ = _read_element(der)
    if element.tag != 0x30:
        raise RsaError("Invalid RSA public key")
    return element.content


def _read_element(der: bytes) -> tuple[_Element, bytes]:
    if len(der) < 2:
        raise RsaError("Invalid RSA public key")
    tag = der[0]
    first = der[1]
    if first < 0x80:
        length = first
        offset = 2
    else:
        count = first & 0x7F
        if count == 0 or len(der) < 2 + count:
            raise RsaError("Invalid RSA public key")
        length = int.from_bytes(der[2 : 2 + count], "big")
        offset = 2 + count
    end = offset + length
    if end > len(der):
        raise RsaError("Invalid RSA public key")
    return _Element(tag, der[offset:end], der[:end]), der[end:]
