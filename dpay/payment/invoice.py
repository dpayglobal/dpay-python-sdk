from __future__ import annotations

from typing import Any

from dpay._internal.validation import is_valid_date
from dpay.exceptions import DPayValueError
from dpay.money import Money


class InvoiceDetails:
    def __init__(self) -> None:
        self.payer_nip: str | None = None
        self.payer_name: str | None = None
        self.invoice_number: str | None = None
        self.payment_due_date: str | None = None
        self.vat_amount: Money | None = None

    @classmethod
    def create(cls) -> InvoiceDetails:
        return cls()

    def with_payer_nip(self, payer_nip: str) -> InvoiceDetails:
        self.payer_nip = payer_nip
        return self

    def with_payer_name(self, payer_name: str) -> InvoiceDetails:
        self.payer_name = payer_name
        return self

    def with_invoice_number(self, invoice_number: str) -> InvoiceDetails:
        self.invoice_number = invoice_number
        return self

    def with_payment_due_date(self, payment_due_date: str) -> InvoiceDetails:
        if not is_valid_date(payment_due_date):
            raise DPayValueError("Payment due date must be in YYYY-MM-DD format")
        self.payment_due_date = payment_due_date
        return self

    def with_vat_amount(self, vat_amount: Money) -> InvoiceDetails:
        self.vat_amount = vat_amount
        return self

    def to_api(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if self.payer_nip is not None:
            data["payer_nip"] = self.payer_nip
        if self.payer_name is not None:
            data["payer_name"] = self.payer_name
        if self.invoice_number is not None:
            data["invoice_number"] = self.invoice_number
        if self.payment_due_date is not None:
            data["payment_due_date"] = self.payment_due_date
        if self.vat_amount is not None:
            data["vat_amount"] = self.vat_amount.minor
        return data
