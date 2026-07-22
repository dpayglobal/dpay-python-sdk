from __future__ import annotations

from dpay._internal.validation import is_valid_url
from dpay.exceptions import DPayValueError


class ReturnUrls:
    def __init__(self, success: str, fail: str, ipn: str) -> None:
        for name, url in (("success", success), ("fail", fail), ("ipn", ipn)):
            if not is_valid_url(url):
                raise DPayValueError(f'Invalid {name} URL "{url}"')
        self.success = success
        self.fail = fail
        self.ipn = ipn
