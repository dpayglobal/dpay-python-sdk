from __future__ import annotations

import hashlib
from typing import Any

from dpay import (
    ApplePayRequest,
    BlikAliasRegistration,
    CardPaymentRequest,
    CardRecurringOperation,
    CardRecurringRegistration,
    Currency,
    DccDecision,
    DeviceInfo,
    DPayClient,
    GooglePayRequest,
    InvoiceDetails,
    IpnVerifier,
    Money,
    Payer,
    PayoutFeeMode,
    PayoutInstruction,
    PayoutPosition,
    RecurringRegistration,
    RegisterPaymentRequest,
    ReturnUrls,
    TransactionType,
    WebhookTarget,
)
from dpay._internal.checksum import ChecksumCalculator
from dpay._internal.php import php_json_encode, php_strval
from dpay.http.models import ApiResponse
from dpay.testing import MockHttpClient

SERVICE = "test_service"
SECRET = "sekret-hash-123"

IPN_CASES: list[dict[str, Any]] = [
    {
        "id": "tx-1",
        "amount": "29.99",
        "email": "jan@example.com",
        "type": "transfer",
        "attempt": 1,
        "version": 2,
        "custom": "order-1",
    },
    {"id": "tx-2", "amount": "10.50", "type": "dcb", "attempt": 3, "version": 1},
    {
        "id": "tx-3",
        "amount": 10.5,
        "email": "",
        "type": "capture",
        "attempt": "1",
        "version": "1",
        "custom": "",
        "capture_payment_id": "cap-9",
    },
    {"id": 4, "amount": 10.0, "type": "transfer", "attempt": 1, "version": 1},
]


class _Recorder(MockHttpClient):
    def request(self, request: Any) -> ApiResponse:
        self.requests.append(request)
        if self.queued:
            return self.queued.pop(0)
        return ApiResponse(200, {}, "{}")


def build_device_info() -> DeviceInfo:
    return DeviceInfo.create(
        "text/html",
        "pl-PL",
        24,
        1080,
        1920,
        -60,
        "Mozilla/5.0",
        "Windows",
        "52.2297,21.0122",
        "device-abc",
        "Sklep Testowy",
    ).with_browser_java_enabled(True)


def ipn_signature(payload: dict[str, Any]) -> str:
    parts = [php_strval(payload["id"]), SECRET, php_strval(payload["amount"])]
    if payload["type"] != "dcb":
        parts.append(php_strval(payload.get("email", "")))
    parts.append(php_strval(payload["type"]))
    parts.append(php_strval(payload["attempt"]))
    parts.append(php_strval(payload["version"]))
    parts.append(php_strval(payload.get("custom", "")))
    return hashlib.sha256("".join(parts).encode()).hexdigest()


def run() -> dict[str, Any]:
    out: dict[str, Any] = {}
    recorder = _Recorder()
    dpay = DPayClient(service=SERVICE, secret_hash=SECRET, http_client=recorder)
    device = build_device_info()

    recorder.queue_json(200, {"transactionId": "tx-1", "msg": "https://secure.dpay.pl/pay/1"})
    dpay.payments.register(
        RegisterPaymentRequest.create(
            Money.pln(2999),
            TransactionType.TRANSFERS,
            ReturnUrls("https://shop.test/ok", "https://shop.test/fail", "https://shop.test/ipn"),
        )
        .with_description("Zamówienie #1234 / ĄĘŚŻ")
        .with_custom("order-1234")
        .with_payer(Payer.create().with_email("jan@example.com").with_name("Jan", "Kowalski"))
        .with_accept_tos(True)
        .with_channel("86")
        .with_credit_card(True)
        .with_paysafecard(False)
        .with_blik(True)
        .with_installment(False)
        .with_paypal(True)
        .with_no_banks(False)
        .with_phone_number("+48123456789", Currency.EUR)
        .with_partner_platform("SHOPIFY01")
        .with_alias_ipn_url("https://shop.test/alias-ipn")
        .with_no_delay(True)
        .with_authorize_only(False)
        .with_card_recurring_operation(CardRecurringOperation.CHARGE)
        .with_payout(
            PayoutInstruction.create(
                [PayoutPosition("PL61109010140000071219812874", "Wypłata 1", Money.pln(1050))],
                PayoutFeeMode.GROSS,
            )
        )
        .with_billing_address({"street": "Testowa 1", "city": "Warszawa"})
        .with_shipping_address({"street": "Inna 2"})
        .with_device_info(device)
        .with_products([{"name": "Produkt", "price": 29.99}])
        .with_efaktura(
            InvoiceDetails.create()
            .with_payer_nip("1234563218")
            .with_payer_name("Firma sp. z o.o.")
            .with_invoice_number("FV/2026/07/1")
            .with_payment_due_date("2026-08-15")
            .with_vat_amount(Money.pln(560))
        )
    )

    recorder.queue_json(200, {"transactionId": "tx-2", "msg": "Transaction paid"})
    dpay.payments.register(
        RegisterPaymentRequest.create(
            Money.pln(1000),
            TransactionType.TRANSFERS,
            ReturnUrls("https://shop.test/ok", "https://shop.test/fail", "https://shop.test/ipn"),
        )
        .with_blik_code("123456", "UA/1.0", "10.0.0.1")
        .with_recurring_registration(
            RecurringRegistration.create(
                "Subskrypcja", RecurringRegistration.MODEL_M, "https://shop.test/regulamin"
            )
            .with_alias("SUB-1")
            .with_frequency("12M")
            .with_limit_amt(100000)
            .with_tot_limit_amt(500000)
            .with_limit_amt_fixed(True)
            .with_expiration_date("2027-01-01")
            .with_init_date("2026-08-01")
            .with_methods([RecurringRegistration.METHOD_BLIK])
            .with_terms_version("2026-09")
        )
    )

    recorder.queue_json(200, {"transactionId": "tx-3", "msg": "ok"})
    dpay.payments.register(
        RegisterPaymentRequest.create(
            Money.of(500, Currency.CZK),
            TransactionType.CARD_RECURRING,
            ReturnUrls("https://shop.test/ok", "https://shop.test/fail", "https://shop.test/ipn"),
        )
        .with_register_blik_alias(BlikAliasRegistration("Moj alias", "UID"))
        .with_card_recurring(
            CardRecurringRegistration.create("Mandat")
            .with_frequency("MONTHLY")
            .with_limit_amt(Money.pln(20000))
            .with_tot_limit_amt(Money.pln(100000))
            .with_limit_amt_fixed(False)
            .with_expiration_date("2028-12-31")
            .with_init_date("2026-09-01")
        )
    )

    recorder.queue_json(200, {"transaction": {"id": "tx-1", "value": "29.99", "status": "paid"}})
    dpay.payments.details("tx-1")

    recorder.queue_json(200, {"status": "success", "refund": True})
    dpay.refunds.create("tx-1")

    recorder.queue_json(200, {"status": "success", "refund": True})
    dpay.refunds.create("tx-1", Money.pln(1050), "reklamacja / zwrot")

    recorder.queue_json(200, {"refund": True, "message": "ok"})
    dpay.refunds.check_availability("tx-1", Money.pln(500))

    recorder.queue_json(200, [{"id": "1", "name": "Bank", "on_from": 0, "on_to": 24}])
    dpay.banks.all()

    recorder.queue_json(200, [{"id": "1", "name": "Bank"}])
    dpay.banks.for_service(1784700000)

    recorder.queue_json(200, {"id": 7, "state": 1, "net": 100.5})
    dpay.payouts.details(4242)

    recorder.queue_json(200, {"id": 7, "state": 1})
    dpay.payouts.details(4242, 1784700000)

    recorder.queue_json(200, {"data": {"alias_value": "a-1", "alias_type": "UID", "status": "ACTIVE"}})
    dpay.blik.alias("a-1")

    recorder.queue_json(200, {"data": {}})
    dpay.blik.unregister_alias("a-1", "UID", "user request")

    recorder.queue_json(200, {"data": {"alias": "a-1"}})
    dpay.recurring.status("a-1")

    recorder.queue_text(200, "-----BEGIN PUBLIC KEY-----\nAAA\n-----END PUBLIC KEY-----\n")
    dpay.cards.public_key()

    recorder.queue_json(200, {"success": True, "message": {"redirectType": "SUCCESS"}})
    dpay.cards.pay_otp(
        "tx 1/2",
        CardPaymentRequest.create(device)
        .with_email("jan@example.com")
        .with_channel_id(86)
        .with_card_holder("Jan", "Kowalski")
        .with_encrypted_card_data("BASE64DATA==")
        .with_three_ds_confirmed(True)
        .with_dcc_decision(DccDecision.ACCEPT),
    )

    recorder.queue_json(200, {"success": True, "message": {"redirectType": "SUCCESS"}})
    dpay.cards.pre_auth("tx-1", CardPaymentRequest.create(device))

    recorder.queue_json(200, {"success": True, "message": {"redirectType": "SUCCESS"}})
    dpay.cards.capture("tx-1", Money.pln(2999))

    recorder.queue_json(200, {"success": True, "message": {"redirectType": "SUCCESS"}})
    dpay.cards.cancel("tx-1")

    recorder.queue_json(200, {"success": True, "message": {"redirectType": "SUCCESS"}})
    dpay.cards.cancel("tx-1", Money.pln(100))

    recorder.queue_json(200, {"success": True, "message": {"redirectType": "SUCCESS"}})
    dpay.cards.google_pay(
        "tx-1",
        GooglePayRequest.create("gp-token", device).with_email("a@b.pl").with_channel_id(90),
    )

    recorder.queue_json(200, {"success": True, "message": {"redirectType": "SUCCESS"}})
    dpay.cards.apple_pay("tx-1", ApplePayRequest.init(device))

    recorder.queue_json(200, {"success": True, "message": {"redirectType": "SUCCESS"}})
    dpay.cards.apple_pay("tx-1", ApplePayRequest.pay("ap-token", device).with_channel_id(91))

    recorder.queue_json(
        200, {"error": False, "msg": "Internal processing", "status": True, "transactionId": "tx-4"}
    )
    dpay.payments.register(
        RegisterPaymentRequest.create(
            Money.pln(4999),
            TransactionType.TRANSFERS,
            ReturnUrls("https://shop.test/ok", "https://shop.test/fail"),
        )
        .with_recurring_alias("SUB-1")
        .with_client_context("UA/1.0", "10.0.0.1")
        .with_description("Abonament 10/2026")
        .with_webhook(
            WebhookTarget.create("https://shop.test/webhooks", ["payment.succeeded", "payment.failed"])
        )
        .with_reference("order-77")
    )

    recorder.queue_json(
        200,
        {"status": "success", "data": {"transactionId": "tx-4", "retry": {"status": "pending", "count": 1}}},
    )
    dpay.recurring.retry("tx-4")

    recorder.queue_json(200, {"status": "success", "data": {"alias": "SUB-1", "status": "UNREGISTERED"}})
    dpay.recurring.cancel("SUB-1", "Rezygnacja")

    recorder.queue_json(200, {"status": "success", "refund": True})
    dpay.refunds.create(
        "tx-1",
        Money.pln(500),
        "reklamacja",
        WebhookTarget.create("https://shop.test/webhooks/refunds", ["refund.succeeded", "refund.failed"]),
    )

    recorder.queue_json(200, {"success": True, "message": {"redirectType": "SUCCESS"}})
    dpay.cards.capture(
        "tx-1",
        Money.pln(1500),
        WebhookTarget.create("https://shop.test/webhooks/captures", ["payment.captured"]),
    )

    recorder.queue_json(
        200, {"status": "success", "data": [], "has_more": False, "next_starting_after": None}
    )
    dpay.events.list(
        types=["payment.succeeded", "refund.failed"],
        created_from="2026-09-01T00:00:00Z",
        limit=10,
        timestamp=1784700000,
    )

    out["calls"] = [
        {"method": call.method, "url": call.url, "headers": call.headers, "body": call.body}
        for call in recorder.requests
    ]

    checksum = ChecksumCalculator(SECRET)
    out["checksums"] = {
        "secret_second_empty": checksum.secret_second(SERVICE, []),
        "secret_second_mixed": checksum.secret_second(SERVICE, ["10.00", 42, 3.5, "https://a/b"]),
        "ordered_simple": checksum.ordered_body([SERVICE, "tx-1"]),
        "ordered_mixed": checksum.ordered_body([SERVICE, 1784700000, 4242, 10.0, True, False, ""]),
    }

    out["money_to_decimal"] = {
        str(minor): Money.pln(minor).to_decimal() for minor in (1050, 1000, 5, 0, -2000, -5, 123456789)
    }

    from_api = [
        30,
        0,
        -7,
        10.5,
        8.285,
        0.1,
        29.999,
        "10",
        "10.5",
        "10.50",
        "0.05",
        "-0.05",
        "abc",
        True,
        None,
    ]
    out["money_try_from_api"] = {}
    for index, value in enumerate(from_api):
        money = Money.try_from_api_number(value, Currency.PLN)
        out["money_try_from_api"][str(index)] = None if money is None else money.minor

    out["float_cast"] = {
        decimal: php_json_encode({"amount": float(decimal)})
        for decimal in ("29.99", "10.00", "0.05", "-20.00", "1234567.89")
    }

    out["strval"] = {
        str(index): php_strval(value)
        for index, value in enumerate(
            [10.0, 10.5, 0.1, 1 / 3, 1e25, -0.0, 100.0, 828.5, True, False, 42, "abc"]
        )
    }

    out["ipn"] = {}
    for index, case in enumerate(IPN_CASES):
        signature = ipn_signature(case)
        payload = {**case, "signature": signature}
        body = php_json_encode(payload, escape_slashes=True)
        event = IpnVerifier.construct_event(body, SECRET)
        out["ipn"][str(index)] = {
            "body": body,
            "signature": signature,
            "id": event.id,
            "amount": event.amount,
            "email": event.email,
            "type": event.type,
            "attempt": event.attempt,
            "version": event.version,
            "custom": event.custom,
            "capture_payment_id": event.capture_payment_id,
        }

    out["card_payload"] = php_json_encode(
        {"PN": "4111111111111111", "SC": "123", "DT": "12/25", "ID": "tx-1", "TX": 1784700000},
        escape_slashes=True,
    )

    return out
