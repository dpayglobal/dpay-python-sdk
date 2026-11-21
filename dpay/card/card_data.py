from __future__ import annotations

import re

from dpay.exceptions import DPayValueError

# Whole string (fullmatch), ASCII digits - ``\d`` matches every Unicode digit and ``$`` a final "\n"
_PAN = re.compile(r"[0-9]{12,19}")
_CVV = re.compile(r"[0-9]{3,4}")
_EXPIRY = re.compile(r"(0[1-9]|1[0-2])/[0-9]{2}")


class CardData:
    def __init__(self, pan: str, cvv: str, expiry: str) -> None:
        normalized_pan = pan.replace(" ", "")
        if _PAN.fullmatch(normalized_pan) is None:
            raise DPayValueError("Card number must be 12-19 digits")
        if _CVV.fullmatch(cvv) is None:
            raise DPayValueError("CVV must be 3-4 digits")
        if _EXPIRY.fullmatch(expiry) is None:
            raise DPayValueError("Expiry must be in MM/YY format")
        self.pan = normalized_pan
        self.cvv = cvv
        self.expiry = expiry

    def __repr__(self) -> str:
        return f"CardData(pan='****{self.pan[-4:]}', cvv='***', expiry='{self.expiry}')"
