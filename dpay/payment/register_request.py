from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

from dpay._internal.validation import byte_length, is_valid_ip, is_valid_url
from dpay.currency import Currency
from dpay.exceptions import DPayValueError
from dpay.money import Money
from dpay.payment.device_info import DeviceInfo
from dpay.payment.enums import TransactionType
from dpay.payment.invoice import InvoiceDetails
from dpay.payment.payer import Payer
from dpay.payment.payout_instruction import PayoutInstruction
from dpay.payment.return_urls import ReturnUrls
from dpay.webhook.event_type import WebhookEventType

if TYPE_CHECKING:
    from dpay.blik.registration import BlikAliasRegistration
    from dpay.card.recurring import CardRecurringRegistration
    from dpay.recurring.registration import RecurringRegistration
    from dpay.webhook.target import WebhookTarget

_PARTNER_PLATFORM = re.compile(r"^[A-Z0-9]{1,64}$")
_BLIK_CODE = re.compile(r"^\d{6}$")
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")
# Characters PHP trim() removes - the API trims strings the same way before validation
_TRIMMED = " \t\n\r\x00\x0b"


class RegisterPaymentRequest:
    def __init__(self, amount: Money, transaction_type: str, urls: ReturnUrls) -> None:
        TransactionType.assert_valid(transaction_type)
        self.amount = amount
        self.transaction_type = transaction_type
        self.urls = urls
        self.description: str | None = None
        self.custom: str | None = None
        self.payer: Payer | None = None
        self.accept_tos: bool | None = None
        self.channel: str | None = None
        self.credit_card: bool | None = None
        self.paysafecard: bool | None = None
        self.blik: bool | None = None
        self.installment: bool | None = None
        self.paypal: bool | None = None
        self.no_banks: bool | None = None
        self.phone_number: str | None = None
        self.currency_code: str | None = None
        self.partner_platform: str | None = None
        self.user_agent: str | None = None
        self.user_ip: str | None = None
        self.blik_code: str | None = None
        self.blik_alias: str | None = None
        self.register_blik_alias: BlikAliasRegistration | None = None
        self.recurring_registration: RecurringRegistration | None = None
        self.recurring_alias: str | None = None
        self.webhook: WebhookTarget | None = None
        self.reference: str | None = None
        self.alias_ipn_url: str | None = None
        self.no_delay: bool | None = None
        self.card_recurring: CardRecurringRegistration | None = None
        self.card_recurring_alias: str | None = None
        self.authorize_only: bool | None = None
        self.card_recurring_operation: str | None = None
        self.payout: PayoutInstruction | None = None
        self.billing_address: Mapping[str, Any] | None = None
        self.shipping_address: Mapping[str, Any] | None = None
        self.device_info: DeviceInfo | None = None
        self.products: Sequence[Mapping[str, Any]] | None = None
        self.efaktura: bool | None = None
        self.invoice: InvoiceDetails | None = None

    @classmethod
    def create(cls, amount: Money, transaction_type: str, urls: ReturnUrls) -> RegisterPaymentRequest:
        return cls(amount, transaction_type, urls)

    def with_description(self, description: str) -> RegisterPaymentRequest:
        self.description = description
        return self

    def with_custom(self, custom: str) -> RegisterPaymentRequest:
        self.custom = custom
        return self

    def with_payer(self, payer: Payer) -> RegisterPaymentRequest:
        self.payer = payer
        return self

    def with_accept_tos(self, accept_tos: bool) -> RegisterPaymentRequest:
        self.accept_tos = accept_tos
        return self

    def with_channel(self, channel: str) -> RegisterPaymentRequest:
        self.channel = channel
        return self

    def with_credit_card(self, enabled: bool) -> RegisterPaymentRequest:
        self.credit_card = enabled
        return self

    def with_paysafecard(self, enabled: bool) -> RegisterPaymentRequest:
        self.paysafecard = enabled
        return self

    def with_blik(self, enabled: bool) -> RegisterPaymentRequest:
        self.blik = enabled
        return self

    def with_installment(self, enabled: bool) -> RegisterPaymentRequest:
        self.installment = enabled
        return self

    def with_paypal(self, enabled: bool) -> RegisterPaymentRequest:
        self.paypal = enabled
        return self

    def with_no_banks(self, disabled: bool) -> RegisterPaymentRequest:
        self.no_banks = disabled
        return self

    def with_phone_number(self, phone_number: str, currency_code: str) -> RegisterPaymentRequest:
        Currency.assert_valid(currency_code)
        self.phone_number = phone_number
        self.currency_code = currency_code
        return self

    def with_currency_code(self, currency_code: str) -> RegisterPaymentRequest:
        Currency.assert_valid(currency_code)
        self.currency_code = currency_code
        return self

    def with_partner_platform(self, partner_platform: str) -> RegisterPaymentRequest:
        if _PARTNER_PLATFORM.match(partner_platform) is None:
            raise DPayValueError("Partner platform must match ^[A-Z0-9]{1,64}$")
        self.partner_platform = partner_platform
        return self

    def with_blik_code(self, blik_code: str, user_agent: str, user_ip: str) -> RegisterPaymentRequest:
        if _BLIK_CODE.match(blik_code) is None:
            raise DPayValueError("BLIK code must be exactly 6 digits")
        if self.blik_alias is not None:
            raise DPayValueError("blik_code cannot be combined with blik_alias")
        self.blik_code = blik_code
        self.user_agent = user_agent
        self.user_ip = user_ip
        return self

    def with_blik_alias(self, alias_value: str, user_agent: str, user_ip: str) -> RegisterPaymentRequest:
        if (
            self.blik_code is not None
            or self.register_blik_alias is not None
            or self.recurring_registration is not None
            or self.recurring_alias is not None
        ):
            raise DPayValueError(
                "blik_alias cannot be combined with blik_code, alias registration or recurring payments"
            )
        self.blik_alias = alias_value
        self.user_agent = user_agent
        self.user_ip = user_ip
        return self

    def with_register_blik_alias(self, registration: BlikAliasRegistration) -> RegisterPaymentRequest:
        if self.blik_alias is not None:
            raise DPayValueError("register_blik_alias cannot be combined with blik_alias")
        self.register_blik_alias = registration
        return self

    def with_recurring_registration(self, registration: RecurringRegistration) -> RegisterPaymentRequest:
        """Registers a recurring payment together with this payment.

        Requires the customer's BLIK code (``with_blik_code``) and transaction type ``transfers``;
        the amount may be 0 (consent only) or an initial fee.
        """
        self.recurring_registration = registration
        return self

    def with_recurring_alias(self, alias: str) -> RegisterPaymentRequest:
        """Charges a registered recurring payment server-to-server (no BLIK code).

        Transaction type ``transfers``, amount above 0. The alias is appended to the checksum,
        binding the charge to that customer.
        """
        if alias == "" or byte_length(alias) > 128:
            raise DPayValueError("Recurring alias must be 1-128 characters")
        self.recurring_alias = alias
        return self

    def with_client_context(self, user_agent: str, user_ip: str) -> RegisterPaymentRequest:
        """Payer's user agent and IP for a recurring charge (optional there).

        BLIK code and alias payments set them in ``with_blik_code`` / ``with_blik_alias``.
        """
        if not is_valid_ip(user_ip):
            raise DPayValueError(f'Invalid user IP "{user_ip}"')
        self.user_agent = user_agent
        self.user_ip = user_ip
        return self

    def with_webhook(self, webhook: WebhookTarget) -> RegisterPaymentRequest:
        """Sends the events of this payment (and later of its refunds and recurring payment) to this URL too.

        Signed with the service's webhook secret. Not part of the checksum.
        """
        webhook.assert_events_allowed(WebhookEventType.PAYMENT_REGISTRATION, "a payment registration")
        self.webhook = webhook
        return self

    def with_reference(self, reference: str) -> RegisterPaymentRequest:
        """Your reference of the payment (max 64 characters), returned as ``references.merchant``."""
        reference = reference.strip(_TRIMMED)
        if reference == "" or len(reference) > 64 or _CONTROL_CHARACTERS.search(reference) is not None:
            raise DPayValueError("Reference must be 1-64 characters without control characters")
        self.reference = reference
        return self

    def with_alias_ipn_url(self, url: str) -> RegisterPaymentRequest:
        if not is_valid_url(url):
            raise DPayValueError(f'Invalid alias IPN URL "{url}"')
        self.alias_ipn_url = url
        return self

    def with_no_delay(self, no_delay: bool) -> RegisterPaymentRequest:
        self.no_delay = no_delay
        return self

    def with_card_recurring(self, registration: CardRecurringRegistration) -> RegisterPaymentRequest:
        if self.card_recurring_alias is not None:
            raise DPayValueError("register_card_recurring cannot be combined with card_recurring_alias")
        self.card_recurring = registration
        return self

    def with_card_recurring_alias(self, alias: str) -> RegisterPaymentRequest:
        if self.card_recurring is not None:
            raise DPayValueError("card_recurring_alias cannot be combined with register_card_recurring")
        self.card_recurring_alias = alias
        return self

    def with_authorize_only(self, authorize_only: bool) -> RegisterPaymentRequest:
        self.authorize_only = authorize_only
        return self

    def with_card_recurring_operation(self, operation: str) -> RegisterPaymentRequest:
        from dpay.card.enums import CardRecurringOperation

        CardRecurringOperation.assert_valid(operation)
        self.card_recurring_operation = operation
        return self

    def with_payout(self, payout: PayoutInstruction) -> RegisterPaymentRequest:
        self.payout = payout
        return self

    def with_billing_address(self, billing_address: Mapping[str, Any]) -> RegisterPaymentRequest:
        self.billing_address = billing_address
        return self

    def with_shipping_address(self, shipping_address: Mapping[str, Any]) -> RegisterPaymentRequest:
        self.shipping_address = shipping_address
        return self

    def with_device_info(self, device_info: DeviceInfo) -> RegisterPaymentRequest:
        self.device_info = device_info
        return self

    def with_products(self, products: Sequence[Mapping[str, Any]]) -> RegisterPaymentRequest:
        self.products = products
        return self

    def with_efaktura(self, invoice: InvoiceDetails | None = None) -> RegisterPaymentRequest:
        if self.transaction_type != TransactionType.TRANSFERS:
            raise DPayValueError('efaktura is allowed only for transactionType "transfers"')
        self.efaktura = True
        self.invoice = invoice
        return self

    def to_api(self, service: str) -> dict[str, Any]:
        self._assert_recurring_combination()

        body: dict[str, Any] = {
            "service": service,
            "value": self.amount.to_decimal(),
            "transactionType": self.transaction_type,
            "url_success": self.urls.success,
            "url_fail": self.urls.fail,
        }
        if self.urls.ipn is not None:
            body["url_ipn"] = self.urls.ipn

        if self.description is not None:
            body["description"] = self.description
        if self.custom is not None:
            body["custom"] = self.custom
        if self.payer is not None:
            if self.payer.email is not None:
                body["email"] = self.payer.email
            if self.payer.first_name is not None:
                body["client_name"] = self.payer.first_name
            if self.payer.last_name is not None:
                body["client_surname"] = self.payer.last_name
        if self.accept_tos is not None:
            body["accept_tos"] = self.accept_tos
        if self.channel is not None:
            body["channel"] = self.channel
        for key, flag in (
            ("creditcard", self.credit_card),
            ("paysafecard", self.paysafecard),
            ("blik", self.blik),
            ("installment", self.installment),
            ("paypal", self.paypal),
            ("nobanks", self.no_banks),
        ):
            if flag is not None:
                body[key] = int(flag)
        if self.phone_number is not None:
            body["phone_number"] = self.phone_number
        if self.currency_code is not None:
            body["currency_code"] = self.currency_code
        if self.partner_platform is not None:
            body["partner_platform"] = self.partner_platform
        if self.user_agent is not None:
            body["user_agent"] = self.user_agent
        if self.user_ip is not None:
            body["user_ip"] = self.user_ip
        if self.blik_code is not None:
            body["blik_code"] = self.blik_code
        if self.blik_alias is not None:
            body["blik_alias"] = self.blik_alias
        if self.register_blik_alias is not None:
            body["register_blik_alias"] = self.register_blik_alias.to_api()
        if self.recurring_registration is not None:
            body["recurring_registration"] = self.recurring_registration.to_api()
        if self.recurring_alias is not None:
            body["recurring_alias"] = self.recurring_alias
        if self.alias_ipn_url is not None:
            body["alias_ipn_url"] = self.alias_ipn_url
        if self.no_delay is not None:
            body["no_delay"] = self.no_delay
        if self.card_recurring is not None:
            body["register_card_recurring"] = self.card_recurring.to_api()
        if self.card_recurring_alias is not None:
            body["card_recurring_alias"] = self.card_recurring_alias
        if self.authorize_only is not None:
            body["authorize_only"] = self.authorize_only
        if self.card_recurring_operation is not None:
            body["card_recurring_operation"] = self.card_recurring_operation
        if self.payout is not None:
            body["payout"] = self.payout.to_api()
        if self.billing_address is not None:
            body["billing_address"] = dict(self.billing_address)
        if self.shipping_address is not None:
            body["shipping_address"] = dict(self.shipping_address)
        if self.device_info is not None:
            body["device_info"] = self.device_info.to_api()
        if self.products is not None:
            body["products"] = [dict(product) for product in self.products]
        if self.efaktura is not None:
            body["efaktura"] = self.efaktura
        if self.invoice is not None:
            body["invoice"] = self.invoice.to_api()
        if self.webhook is not None:
            body["webhook"] = self.webhook.to_api()
        if self.reference is not None:
            body["reference"] = self.reference

        return body

    def _assert_recurring_combination(self) -> None:
        if self.recurring_registration is None and self.recurring_alias is None:
            return
        if self.recurring_registration is not None and self.recurring_alias is not None:
            raise DPayValueError("recurring_registration cannot be combined with recurring_alias")
        if self.transaction_type != TransactionType.TRANSFERS:
            raise DPayValueError('Recurring payments require transactionType "transfers"')
        conflicts: list[tuple[str, object]] = [
            ("blik_alias", self.blik_alias),
            ("register_blik_alias", self.register_blik_alias),
            ("register_card_recurring", self.card_recurring),
            ("card_recurring_alias", self.card_recurring_alias),
        ]
        if self.recurring_registration is not None:
            conflicts.append(("channel", self.channel))
            if self.blik_code is None:
                raise DPayValueError(
                    "recurring_registration requires the customer's BLIK code (with_blik_code)"
                )
        else:
            conflicts.append(("blik_code", self.blik_code))
            if self.amount.minor <= 0:
                raise DPayValueError("A recurring charge requires an amount above 0")
        for field, value in conflicts:
            if value is not None:
                raise DPayValueError(f"{field} cannot be combined with a recurring payment")
