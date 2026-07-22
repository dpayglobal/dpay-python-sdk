from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dpay.bank.models import Bank
from dpay.blik.models import BlikAlias, BlikRecurringStatus
from dpay.card.results import CardPaymentResult
from dpay.money import Money
from dpay.payment.models import RegisteredPayment, Transaction
from dpay.payout.models import PayoutDetails
from dpay.refund.models import Refund, RefundAvailability

FIXTURES: dict[str, list[Any]] = json.loads(
    (Path(__file__).parent / "golden" / "response_fixtures.json").read_text("utf-8")
)


def _money(amount: Money | None) -> dict[str, Any] | None:
    if amount is None:
        return None
    return {"minor": amount.minor, "currency": amount.currency, "decimal": amount.to_decimal()}


def run() -> dict[str, Any]:
    out: dict[str, Any] = {}

    out["registered"] = {
        str(index): _registered(RegisteredPayment.from_api(data))
        for index, data in enumerate(FIXTURES["registered"])
    }
    out["transaction"] = {
        str(index): _transaction(Transaction.from_api(data))
        for index, data in enumerate(FIXTURES["transaction"])
    }
    out["bank"] = {str(index): _bank(Bank.from_api(data)) for index, data in enumerate(FIXTURES["bank"])}
    out["refund"] = {
        str(index): {"is_accepted": refund.is_accepted, "message": refund.message}
        for index, refund in enumerate(Refund.from_api(data) for data in FIXTURES["refund"])
    }
    out["availability"] = {
        str(index): {
            "is_available": availability.is_available,
            "message": availability.message,
            "http_status": availability.http_status,
        }
        for index, availability in enumerate(
            RefundAvailability.from_api(data, 200) for data in FIXTURES["availability"]
        )
    }
    out["payout"] = {
        str(index): _payout(PayoutDetails.from_api(data)) for index, data in enumerate(FIXTURES["payout"])
    }
    out["blik_alias"] = {
        str(index): _blik_alias(BlikAlias.from_api(data)) for index, data in enumerate(FIXTURES["blik_alias"])
    }
    out["blik_recurring"] = {
        str(index): _blik_recurring(BlikRecurringStatus.from_api(data))
        for index, data in enumerate(FIXTURES["blik_recurring"])
    }
    out["card_result"] = {
        str(index): _card_result(CardPaymentResult.from_api(data))
        for index, data in enumerate(FIXTURES["card_result"])
    }
    return out


def _registered(payment: RegisteredPayment) -> dict[str, Any]:
    return {
        "transaction_id": payment.transaction_id,
        "message": payment.message,
        "redirect_url": payment.redirect_url,
        "is_paid": payment.is_paid,
        "is_internal_processing": payment.is_internal_processing,
        "ipksef": payment.ipksef,
        "card_recurring_alias": payment.card_recurring_alias,
    }


def _transaction(transaction: Transaction) -> dict[str, Any]:
    return {
        "id": transaction.id,
        "value": _money(transaction.value),
        "status": transaction.status,
        "is_paid": transaction.is_paid,
        "payment_method": transaction.payment_method,
        "creation_date": transaction.creation_date,
        "payment_date": transaction.payment_date,
        "is_settled": transaction.is_settled,
        "is_refunded": transaction.is_refunded,
        "refunded_amount": _money(transaction.refunded_amount),
        "available_refund_amount": _money(transaction.available_refund_amount),
        "is_fully_refunded": transaction.is_fully_refunded,
        "is_direct": transaction.is_direct,
        "gateway_id": transaction.gateway_id,
        "payer": transaction.payer,
        "refunds": [
            {
                "payment_id": refund.payment_id,
                "value": _money(refund.value),
                "status": refund.status,
                "creation_date": refund.creation_date,
                "payment_date": refund.payment_date,
            }
            for refund in transaction.refunds
        ],
    }


def _bank(bank: Bank) -> dict[str, Any]:
    return {
        "id": bank.id,
        "name": bank.name,
        "image": bank.image,
        "on_from": bank.on_from,
        "on_to": bank.on_to,
        "iterator": bank.iterator,
        "is_test": bank.is_test,
        "type": bank.type,
    }


def _payout(payout: PayoutDetails) -> dict[str, Any]:
    receiver = payout.receiver
    return {
        "id": payout.id,
        "state": payout.state,
        "is_waiting": payout.is_waiting,
        "is_processed": payout.is_processed,
        "is_failed": payout.is_failed,
        "net": _money(payout.net),
        "fee": _money(payout.fee),
        "gross": _money(payout.gross),
        "creation_date": payout.creation_date,
        "is_direct_settlement": payout.is_direct_settlement,
        "nrb": payout.nrb,
        "is_declined": payout.is_declined,
        "decline_reason": payout.decline_reason,
        "decline_status": payout.decline_status,
        "receiver": None
        if receiver is None
        else {
            "nrb": receiver.nrb,
            "title": receiver.title,
            "amount": _money(receiver.amount),
            "service": receiver.service,
            "receiver_name": receiver.receiver_name,
            "receiver_address": receiver.receiver_address,
        },
    }


def _blik_alias(alias: BlikAlias) -> dict[str, Any]:
    return {
        "alias_value": alias.alias_value,
        "alias_type": alias.alias_type,
        "status": alias.status,
        "is_active": alias.is_active,
        "expiration_date": alias.expiration_date,
        "apps": [{"key": app.key, "label": app.label} for app in alias.apps],
    }


def _blik_recurring(status: BlikRecurringStatus) -> dict[str, Any]:
    registration = status.registration
    return {
        "alias_value": status.alias_value,
        "alias_type": status.alias_type,
        "status": status.status,
        "is_active": status.is_active,
        "expiration_date": status.expiration_date,
        "registration": None
        if registration is None
        else {
            "model": registration.model,
            "frequency": registration.frequency,
            "limit_amt": registration.limit_amt,
            "tot_limit_amt": registration.tot_limit_amt,
            "is_limit_amt_fixed": registration.is_limit_amt_fixed,
            "init_date": registration.init_date,
            "label": registration.label,
            "registered_at": registration.registered_at,
        },
    }


def _card_result(result: CardPaymentResult) -> dict[str, Any]:
    offer = result.dcc_offer
    return {
        "redirect_type": result.redirect_type,
        "is_success": result.is_success,
        "requires_three_ds_form": result.requires_three_ds_form,
        "requires_redirect": result.requires_redirect,
        "has_dcc_offer": result.has_dcc_offer,
        "three_ds_form_html": result.three_ds_form_html,
        "redirect_url": result.redirect_url,
        "dcc_offer": None
        if offer is None
        else {
            "currency_conversion_id": offer.currency_conversion_id,
            "original_amount": _money(offer.original_amount),
            "converted_amount": _money(offer.converted_amount),
            "exchange_rate": offer.exchange_rate,
            "valid_until": offer.valid_until,
            "declaration_text": offer.declaration_text,
            "is_european_economic_area": offer.is_european_economic_area,
            "markup": [
                {"rate": markup.rate, "additional_info": markup.additional_info} for markup in offer.markup
            ],
        },
    }
