from __future__ import annotations

from dpay._internal.validation import is_valid_url
from dpay.exceptions import DPayValueError


class ReturnUrls:
    """Return addresses of a payment. Without ``ipn`` no IPN is sent (the outcome comes as a webhook)."""

    def __init__(self, success: str, fail: str, ipn: str | None = None) -> None:
        for name, url in (("success", success), ("fail", fail), ("ipn", ipn)):
            if url is not None and not is_valid_url(url):
                raise DPayValueError(f'Invalid {name} URL "{url}"')
        self.success = success
        self.fail = fail
        self.ipn = ipn
