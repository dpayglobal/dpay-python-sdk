from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlsplit

# Whole string (fullmatch), ASCII digits - ``\d`` matches every Unicode digit and ``$`` a final "\n"
_EMAIL = re.compile(r"[^@\s]+@[^@\s.]+(\.[^@\s.]+)+")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


def is_valid_url(url: str) -> bool:
    if url == "" or any(character.isspace() for character in url):
        return False
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    return parts.scheme != "" and parts.netloc != ""


def is_valid_ip(ip: str) -> bool:
    # IPv6 zone ids ("fe80::1%eth0") are not client addresses - PHP FILTER_VALIDATE_IP rejects them too
    if "%" in ip:
        return False
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        return False
    return True


def byte_length(text: str) -> int:
    """Length in UTF-8 bytes - PHP ``strlen`` (``len()`` counts characters like ``mb_strlen``)."""
    return len(text.encode("utf-8", "surrogatepass"))


def is_valid_email(email: str) -> bool:
    # PHP FILTER_VALIDATE_EMAIL (without FILTER_FLAG_EMAIL_UNICODE) rejects non-ASCII addresses
    return email.isascii() and _EMAIL.fullmatch(email) is not None


def is_valid_date(date: str) -> bool:
    return _DATE.fullmatch(date) is not None


def assert_date(date: str) -> str:
    from dpay.exceptions import DPayValueError

    if not is_valid_date(date):
        raise DPayValueError(f'Date "{date}" must be in YYYY-MM-DD format')
    return date
