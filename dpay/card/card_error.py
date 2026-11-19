from __future__ import annotations

from typing import Any

from dpay._internal.php import is_php_int


def _string(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if isinstance(value, str):
        return value
    return str(value) if is_php_int(value) else None


class CardError:
    """Card decline details - every field can be ``None``.

    The ``error`` object of a declined card operation (HTTP 200, ``success: false``) and the ``cardError``
    object of a Payments API error (e.g. a declined charge on a saved card).
    """

    def __init__(self, code: str | None, decline_code: str | None, decline_message: str | None) -> None:
        # Stable dpay reason, e.g. ``payment_declined``, ``invalid_card``, ``card_already_registered``.
        self.code = code
        # Two-character card network response code (ISO 8583), e.g. ``05``, ``51``; ``None`` when the
        # decline did not come from an authorisation.
        self.decline_code = decline_code
        # English description of the decline code - localise from ``decline_code``, not from this text.
        self.decline_message = decline_message

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> CardError:
        return cls(_string(data, "code"), _string(data, "declineCode"), _string(data, "declineMessage"))
