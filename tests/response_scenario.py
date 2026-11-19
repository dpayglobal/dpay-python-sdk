from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dpay.bank.models import Bank
from dpay.blik.models import BlikAlias
from dpay.card.card_error import CardError
from dpay.card.results import CardPaymentResult
from dpay.ipn.alias_update import AliasUpdate
from dpay.money import Money
from dpay.payment.models import RegisteredPayment, Transaction
from dpay.payout.models import PayoutDetails, PayoutListItem, PayoutPage, PayoutSettlement
from dpay.recurring.models import RecurringRetryResult, RecurringStatus
from dpay.refund.models import Refund, RefundAvailability
from dpay.webhook.event import WebhookEvent
from dpay.webhook.failure import Failure

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
    out["card_result"] = {
        str(index): _card_result(CardPaymentResult.from_api(data))
        for index, data in enumerate(FIXTURES["card_result"])
    }
    out["recurring_status"] = {
        str(index): _recurring_status(RecurringStatus.from_api(data))
        for index, data in enumerate(FIXTURES["recurring_status"])
    }
    out["recurring_retry"] = {
        str(index): _recurring_retry(RecurringRetryResult.from_api(data))
        for index, data in enumerate(FIXTURES["recurring_retry"])
    }
    out["webhook_event"] = {
        str(index): _webhook_event(WebhookEvent.from_api(data))
        for index, data in enumerate(FIXTURES["webhook_event"])
    }

    # 0.3.0
    out["registered_v3"] = {
        str(index): _registered_v3(RegisteredPayment.from_api(item["data"], item["currency"]))
        for index, item in enumerate(FIXTURES["registered_v3"])
    }
    out["transaction_v3"] = {
        str(index): _transaction_v3(Transaction.from_api(data))
        for index, data in enumerate(FIXTURES["transaction_v3"])
    }
    out["payout_v3"] = {
        str(index): _payout_v3(PayoutDetails.from_api(data))
        for index, data in enumerate(FIXTURES["payout_v3"])
    }
    out["payout_page"] = {
        str(index): _payout_page(PayoutPage.from_api(data))
        for index, data in enumerate(FIXTURES["payout_page"])
    }
    out["payout_settlement"] = {
        str(index): _payout_settlement(PayoutSettlement.from_api(data))
        for index, data in enumerate(FIXTURES["payout_settlement"])
    }
    out["webhook_object"] = {
        str(index): _webhook_object(WebhookEvent.from_api(data))
        for index, data in enumerate(FIXTURES["webhook_object"])
    }
    out["alias_update"] = {
        str(index): _alias_update(AliasUpdate.from_api(data))
        for index, data in enumerate(FIXTURES["alias_update"])
    }
    out["card_error"] = {
        str(index): {
            "code": error.code,
            "decline_code": error.decline_code,
            "decline_message": error.decline_message,
        }
        for index, error in enumerate(CardError.from_api(data) for data in FIXTURES["card_error"])
    }
    out["merchant_session"] = {
        str(index): {"session": CardPaymentResult.from_api(data).apple_pay_merchant_session}
        for index, data in enumerate(FIXTURES["merchant_session"])
    }
    return out


def _registered_v3(payment: RegisteredPayment) -> dict[str, Any]:
    multibanco = payment.multibanco
    paid = payment.paid_transaction
    return {
        "multibanco": None
        if multibanco is None
        else {
            "entity": multibanco.entity,
            "reference": multibanco.reference,
            "amount": _money(multibanco.amount),
            "currency": multibanco.currency,
            "expires_at": multibanco.expires_at,
        },
        "paid_transaction": None
        if paid is None
        else {
            "payment_id": paid.payment_id,
            "status": paid.status,
            "is_paid": paid.is_paid,
            "value": _money(paid.value),
            "email": paid.email,
            "description": paid.description,
            "name": paid.name,
            "surname": paid.surname,
            "pid": paid.pid,
            "mtid": paid.mtid,
            "creation_date": paid.creation_date,
            "payment_date": paid.payment_date,
        },
    }


def _transaction_v3(transaction: Transaction) -> dict[str, Any]:
    urls = transaction.urls
    return {
        "rate": transaction.rate,
        "minimal_fee": transaction.minimal_fee,
        "permanent_fee": transaction.permanent_fee,
        "urls": None if urls is None else {"success": urls.success, "fail": urls.fail, "ipn": urls.ipn},
    }


def _payout_v3(payout: PayoutDetails) -> dict[str, Any]:
    receiver = payout.receiver
    return {
        "currency": payout.currency,
        "net": _money(payout.net),
        "gross": _money(payout.gross),
        "export_date": payout.export_date,
        "is_paysafecard": payout.is_paysafecard,
        "is_processed": payout.is_processed,
        "is_failed": payout.is_failed,
        "receiver_amount": None if receiver is None else _money(receiver.amount),
    }


def _payout_list_item(item: PayoutListItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "type": item.type,
        "state": item.state,
        "is_waiting": item.is_waiting,
        "is_processed": item.is_processed,
        "is_failed": item.is_failed,
        "net": _money(item.net),
        "fee": _money(item.fee),
        "gross": _money(item.gross),
        "currency": item.currency,
        "creation_date": item.creation_date,
        "export_date": item.export_date,
        "is_declined": item.is_declined,
    }


def _page_meta(meta: Any) -> dict[str, Any]:
    return {
        "page": meta.page,
        "per_page": meta.per_page,
        "total": meta.total,
        "total_pages": meta.total_pages,
        "has_more": meta.has_more,
    }


def _payout_page(page: PayoutPage) -> dict[str, Any]:
    return {
        "items": [_payout_list_item(item) for item in page.items],
        "meta": _page_meta(page.meta),
        "has_more": page.has_more,
    }


def _payout_settlement(settlement: PayoutSettlement) -> dict[str, Any]:
    return {
        "settlement": _payout_v3(settlement.settlement),
        "summary_net": _money(settlement.summary_net),
        "summary_fee": _money(settlement.summary_fee),
        "summary_gross": _money(settlement.summary_gross),
        "summary_count": settlement.summary_count,
        "positions": [
            {
                "payment_id": position.payment_id,
                "date": position.date,
                "net": _money(position.net),
                "fee": _money(position.fee),
                "gross": _money(position.gross),
                "service_id": position.service_id,
                "service_name": position.service_name,
                "custom": position.custom,
                "ipksef": position.ipksef,
            }
            for position in settlement.positions
        ],
        "meta": _page_meta(settlement.meta),
    }


def _failure(failure: Failure | None) -> dict[str, Any] | None:
    if failure is None:
        return None
    return {
        "code": failure.code,
        "message": failure.message,
        "category": failure.category,
        "is_retryable": failure.is_retryable,
        "provider_code": failure.provider_code,
    }


def _webhook_object(event: WebhookEvent) -> dict[str, Any]:
    payment = event.payment
    refund = event.refund
    recurring = event.recurring_payment
    payout = event.payout
    return {
        "payment": None
        if payment is None
        else {
            "id": payment.id,
            "status": payment.status,
            "currency": payment.currency,
            "amount": _money(payment.amount),
            "amount_refunded": _money(payment.amount_refunded),
            "amount_captured": _money(payment.amount_captured),
            "description": payment.description,
            "created": payment.created,
            "paid_at": payment.paid_at,
            "payment_method_type": payment.payment_method_type,
            "failure": _failure(payment.failure),
            "is_recurring": payment.is_recurring,
            "recurring_alias": payment.recurring_alias,
            "recurring_registration": payment.recurring_registration,
            "recurring_sequence": payment.recurring_sequence,
            "merchant_reference": payment.merchant_reference,
            "provider_reference": payment.provider_reference,
            "custom": payment.custom,
        },
        "refund": None
        if refund is None
        else {
            "id": refund.id,
            "payment": refund.payment,
            "status": refund.status,
            "currency": refund.currency,
            "amount": _money(refund.amount),
            "created": refund.created,
            "succeeded_at": refund.succeeded_at,
            "failure": _failure(refund.failure),
        },
        "recurring_payment": None
        if recurring is None
        else {
            "id": recurring.id,
            "alias": recurring.alias,
            "status": recurring.status,
            "canceled_by": recurring.canceled_by,
            "payment_method_type": recurring.payment_method_type,
            "model": recurring.model,
            "frequency": recurring.frequency,
            "limit_amount": recurring.limit_amount,
            "total_limit_amount": recurring.total_limit_amount,
            "starts_on": recurring.starts_on,
            "expires_on": recurring.expires_on,
            "created": recurring.created,
        },
        "payout": None
        if payout is None
        else {
            "id": payout.id,
            "status": payout.status,
            "currency": payout.currency,
            "amount": _money(payout.amount),
            "fee": _money(payout.fee),
            "bank_account_last4": payout.bank_account_last4,
            "created": payout.created,
            "paid_at": payout.paid_at,
            "failure": _failure(payout.failure),
        },
    }


def _alias_update(alias: AliasUpdate) -> dict[str, Any]:
    return {
        "change_type": alias.change_type,
        "alias_type": alias.alias_type,
        "alias_status": alias.alias_status,
        "is_active": alias.is_active,
        "alias_key": alias.alias_key,
        "alias_label": alias.alias_label,
        "alias_expire_at": alias.alias_expire_at,
        "change_reason_category": alias.change_reason_category,
        "change_reason_message": alias.change_reason_message,
    }


def _registered(payment: RegisteredPayment) -> dict[str, Any]:
    return {
        "transaction_id": payment.transaction_id,
        "message": payment.message,
        "redirect_url": payment.redirect_url,
        "is_paid": payment.is_paid,
        "is_internal_processing": payment.is_internal_processing,
        "ipksef": payment.ipksef,
        "card_recurring_alias": payment.card_recurring_alias,
        "recurring_alias": payment.recurring_alias,
        "recurring_methods": payment.recurring_methods,
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


def _recurring_status(status: RecurringStatus) -> dict[str, Any]:
    registration = status.registration
    return {
        "alias": status.alias,
        "method": status.method,
        "status": status.status,
        "is_active": status.is_active,
        "expiration_date": status.expiration_date,
        "registration": None
        if registration is None
        else {
            "transaction_id": registration.transaction_id,
            "label": registration.label,
            "model": registration.model,
            "frequency": registration.frequency,
            "limit_amt": registration.limit_amt,
            "tot_limit_amt": registration.tot_limit_amt,
            "is_limit_amt_fixed": registration.is_limit_amt_fixed,
            "init_date": registration.init_date,
            "terms_url": registration.terms_url,
            "terms_version": registration.terms_version,
            "registered_at": registration.registered_at,
        },
    }


def _recurring_retry(retry: RecurringRetryResult) -> dict[str, Any]:
    return {
        "transaction_id": retry.transaction_id,
        "status": retry.status,
        "is_pending": retry.is_pending,
        "is_failed": retry.is_failed,
        "count": retry.count,
        "error_code": retry.error_code,
        "error_description": retry.error_description,
    }


def _webhook_event(event: WebhookEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "type": event.type,
        "api_version": event.api_version,
        "created": event.created,
        "livemode": event.is_livemode,
        "service": event.service,
        "merchant_ref": event.merchant_ref,
        "object_type": event.object_type,
        "object": event.object,
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
