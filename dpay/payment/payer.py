from __future__ import annotations

from dpay._internal.validation import is_valid_email
from dpay.exceptions import DPayValueError


class Payer:
    def __init__(self) -> None:
        self.email: str | None = None
        self.first_name: str | None = None
        self.last_name: str | None = None

    @classmethod
    def create(cls) -> Payer:
        return cls()

    def with_email(self, email: str) -> Payer:
        if not is_valid_email(email):
            raise DPayValueError(f'Invalid email "{email}"')
        self.email = email
        return self

    def with_name(self, first_name: str, last_name: str) -> Payer:
        self.first_name = first_name
        self.last_name = last_name
        return self
