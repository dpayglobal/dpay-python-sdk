"""Every validation pattern matches the whole string with ASCII digits: Python ``re.match(r"...$")`` also
matches before a final "\\n" and ``\\d`` / ``\\s`` match Unicode digits and spaces."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from dpay import (
    CardData,
    CardRecurringRegistration,
    Currency,
    DPayClient,
    DPayValueError,
    InvoiceDetails,
    Money,
    Payer,
    PayoutPosition,
    RecurringRegistration,
    RegisterPaymentRequest,
    ReturnUrls,
    SignatureVerificationError,
    TransactionType,
    WebhookVerifier,
)
from dpay._internal import base_urls
from dpay._internal.operation import Operation
from dpay._internal.php import is_numeric, php_int
from dpay._internal.requestor import ApiRequestor
from dpay.config import Config
from dpay.payment.models import Transaction
from dpay.payout.models import PayoutDetails, PayoutListItem
from dpay.testing import MockHttpClient

TX = "30D9493D-1D73-3FBD-A5D4-633723CC7A68"
URLS = ReturnUrls("https://shop.example/ok", "https://shop.example/fail", "https://shop.example/ipn")


def _client() -> DPayClient:
    return DPayClient(service="MyShop", secret_hash="secret123", http_client=MockHttpClient())


def _request() -> RegisterPaymentRequest:
    return RegisterPaymentRequest.create(Money.pln(1000), TransactionType.TRANSFERS, URLS)


def _recurring() -> RecurringRegistration:
    return RecurringRegistration.create(
        "Abonament", RecurringRegistration.MODEL_O, "https://shop.example/terms"
    )


def _header(name: str) -> object:
    api = ApiRequestor(Config.from_dict({"service": "MyShop", "secret_hash": "secret123"}), MockHttpClient())
    return api.build_request(
        Operation("POST", base_urls.PANEL, "/x", lambda response: None, {}, headers={name: "1"})
    )


REJECTED: dict[str, tuple[Callable[[], object], str]] = {
    "extra header name": (lambda: _header("X-Id\n"), 'Invalid request header "X-Id\n"'),
    "refund message id": (
        lambda: _client().refunds.create(TX, message_id="RET\n"),
        "Refund message ID must be non-empty printable ASCII",
    ),
    "card number": (
        lambda: CardData("4111111111111111\n", "123", "12/30"),
        "Card number must be 12-19 digits",
    ),
    "card number unicode digits": (
        lambda: CardData("411111111111111\u0661", "123", "12/30"),
        "Card number must be 12-19 digits",
    ),
    "cvv": (lambda: CardData("4111111111111111", "123\n", "12/30"), "CVV must be 3-4 digits"),
    "cvv unicode digits": (
        lambda: CardData("4111111111111111", "\uff11\uff12\uff13", "12/30"),
        "CVV must be 3-4 digits",
    ),
    "expiry": (lambda: CardData("4111111111111111", "123", "12/30\n"), "Expiry must be in MM/YY format"),
    "card recurring date": (
        lambda: CardRecurringRegistration.create("Abonament").with_init_date("2026-12-01\n"),
        'Date "2026-12-01\n" must be in YYYY-MM-DD format',
    ),
    "money decimal": (lambda: Money.from_decimal("10.00\n", Currency.PLN), 'Invalid money amount "10.00\n"'),
    "money unicode digits": (
        lambda: Money.from_decimal("\u0661\u0660", Currency.PLN),
        'Invalid money amount "\u0661\u0660"',
    ),
    "invoice due date": (
        lambda: InvoiceDetails.create().with_payment_due_date("2026-12-01\n"),
        "Payment due date must be in YYYY-MM-DD format",
    ),
    "invoice due date unicode digits": (
        lambda: InvoiceDetails.create().with_payment_due_date("\u0662026-12-01"),
        "Payment due date must be in YYYY-MM-DD format",
    ),
    "partner platform": (
        lambda: _request().with_partner_platform("SHOPER\n"),
        "Partner platform must match ^[A-Z0-9]{1,64}$",
    ),
    "blik code": (
        lambda: _request().with_blik_code("123456\n", "Mozilla/5.0", "203.0.113.10"),
        "BLIK code must be exactly 6 digits",
    ),
    "blik code unicode digits": (
        lambda: _request().with_blik_code("12345\u0666", "Mozilla/5.0", "203.0.113.10"),
        "BLIK code must be exactly 6 digits",
    ),
    "recurring frequency": (
        lambda: _recurring().with_frequency("1M\n"),
        'Invalid recurring frequency "1M\n"',
    ),
    "recurring date": (
        lambda: _recurring().with_init_date("2026-12-01\n"),
        'Date "2026-12-01\n" must be in YYYY-MM-DD format',
    ),
    "events starting_after": (
        lambda: _client().events.list(starting_after="evt_01k6a8q2m4pz7h8c3v5n9t2x6y\n"),
        "starting_after must be an event id (evt_...)",
    ),
    "payer email": (
        lambda: Payer.create().with_email("jan@example.com\n"),
        'Invalid email "jan@example.com\n"',
    ),
    "payer email non-ascii": (
        lambda: Payer.create().with_email("zaż@example.com"),
        'Invalid email "zaż@example.com"',
    ),
}


@pytest.mark.parametrize("name", sorted(REJECTED))
def test_trailing_newline_and_unicode_digits_are_rejected(name: str) -> None:
    call, message = REJECTED[name]
    with pytest.raises(DPayValueError) as error:
        call()
    assert str(error.value) == message


def test_values_that_are_not_validated() -> None:
    assert not Currency.is_valid("PLN\n")
    assert Money.try_from_api_number("10.00\n", Currency.PLN) is None
    assert Money.try_from_api_number("\u0661\u0660", Currency.PLN) is None
    assert not PayoutPosition.is_valid_polish_iban("PL61109010140000071219812874\u0661")
    assert PayoutPosition.is_valid_polish_iban("PL61 1090 1014 0000 0712 1981 2874\n")


def test_transaction_integer_field_with_trailing_newline_is_none() -> None:
    transaction = Transaction.from_api({"transaction": {"minimal_fee": "30\n", "permanent_fee": "30"}})
    assert transaction.minimal_fee is None
    assert transaction.permanent_fee == 30
    assert Transaction.from_api({"transaction": {"minimal_fee": "\u0663\u0660"}}).minimal_fee is None


def test_webhook_timestamp_with_trailing_newline_is_rejected() -> None:
    with pytest.raises(SignatureVerificationError, match=r"^Invalid webhook-timestamp header$"):
        WebhookVerifier.verify(
            "{}",
            {
                "webhook-id": "evt_01k6a8q2m4pz7h8c3v5n9t2x6y",
                "webhook-timestamp": "1790503500\n",
                "webhook-signature": "v1,x",
            },
            "whsec_ZHBheS1zZGstc3ludGhldGljLXRlc3Qtc2VjcmV0ISE=",
            300,
            1790503500,
        )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1, True),
        (0, False),
        ("1", False),
        ("1abc", False),
        (True, False),
        (1.0, False),
        (2, False),
        (None, False),
    ],
    ids=["int-1", "int-0", "str-1", "str-1abc", "true", "float-1.0", "int-2", "null"],
)
def test_payout_flags_are_true_only_for_the_json_integer_1(value: object, expected: bool) -> None:
    details = PayoutDetails.from_api(
        {"id": 1, "paysafecard": value, "direct_settlement": value, "declined": value}
    )
    item = PayoutListItem.from_api({"id": 1, "declined": value})

    assert details.is_paysafecard is expected
    assert details.is_direct_settlement is expected
    assert details.is_declined is expected
    assert item.is_declined is expected


@pytest.mark.parametrize(
    ("value", "numeric", "integer"),
    [
        (" 12 ", True, 12),
        ("12\n", True, 12),
        ("\x0b7", True, 7),
        ("1e3", True, 1000),
        (".5", True, 0),
        ("5.", True, 5),
        ("+.5", True, 0),
        ("1.9e1", True, 19),
        ("12abc", False, 12),
        ("  -12.7abc", False, -12),
        ("1e", False, 1),
        ("0x1A", False, 0),
        ("-", False, 0),
        ("", False, 0),
        # Python's float()/int()/str.strip() accept these, PHP does not
        ("\u0661\u0662", False, 0),
        ("\u00b2", False, 0),
        ("\u00a012", False, 0),
        ("\x1c12", False, 0),
        ("1_0", False, 1),
        ("nan", False, 0),
        ("inf", False, 0),
        # PHP 8 (int) saturates integer strings, infinite floats give 0
        ("99999999999999999999", True, 2**63 - 1),
        ("-99999999999999999999", True, -(2**63)),
        ("1e30", True, 2**63 - 1),
        ("1e999", True, 0),
    ],
)
def test_php_numeric_strings_use_ascii_digits_and_php_whitespace(
    value: str, numeric: bool, integer: int
) -> None:
    assert is_numeric(value) is numeric
    assert php_int(value) == integer


def test_public_key_is_trimmed_like_php_trim() -> None:
    transport = MockHttpClient()
    transport.queue_text(200, "\x00 KEY\u00a0\x1c\n\x0b")
    client = DPayClient(service="MyShop", secret_hash="secret123", http_client=transport)
    assert client.cards.public_key() == "KEY\u00a0\x1c"


def test_pem_body_accepts_only_ascii_whitespace() -> None:
    from dpay._internal.rsa import RsaError, load_public_key

    with pytest.raises(RsaError):
        load_public_key("-----BEGIN PUBLIC KEY-----\nAAAA\u00a0AAAA\n-----END PUBLIC KEY-----")
