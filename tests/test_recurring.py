"""Recurring payments: registration, charges, status, retry and cancel (SDK 0.2.0)."""

from __future__ import annotations

import hashlib
from collections.abc import Callable

import pytest

from dpay import (
    BlikAliasRegistration,
    CardRecurringRegistration,
    DPayClient,
    DPayValueError,
    InvalidRequestError,
    Money,
    RecurringRegistration,
    RecurringStatus,
    RegisterPaymentRequest,
    ReturnUrls,
    TransactionType,
    WebhookTarget,
)
from dpay.testing import MockHttpClient
from tests import api_vectors

TERMS = "https://shop.example/terms"
TRANSACTION_ID = api_vectors.TRANSACTION_ID


@pytest.fixture
def vectors_client(transport: MockHttpClient) -> DPayClient:
    return DPayClient(service=api_vectors.SERVICE, secret_hash=api_vectors.SECRET_HASH, http_client=transport)


def _checksum(name: str) -> str:
    return str(api_vectors.vector(api_vectors.SECRET_SECOND, name)["checksum"])


def _urls(ipn: str | None = "https://shop.example/ipn") -> ReturnUrls:
    return ReturnUrls("https://shop.example/ok", "https://shop.example/fail", ipn)


def _registration() -> RecurringRegistration:
    return RecurringRegistration.create("Abonament", RecurringRegistration.MODEL_O, TERMS).with_alias(
        "SUB-0001"
    )


# RecurringRegistration


def test_model_o_sends_no_frequency_or_limits() -> None:
    registration = (
        RecurringRegistration.create("Abonament", RecurringRegistration.MODEL_O, TERMS)
        .with_alias("SUB-0001")
        .with_methods([RecurringRegistration.METHOD_BLIK])
        .with_terms_version("2026-09")
    )
    assert registration.to_api() == {
        "label": "Abonament",
        "alias": "SUB-0001",
        "model": "O",
        "methods": ["blik"],
        "terms_url": TERMS,
        "terms_version": "2026-09",
    }
    assert list(registration.to_api()) == ["label", "alias", "model", "methods", "terms_url", "terms_version"]


@pytest.mark.parametrize(
    ("field", "setter"),
    [
        ("frequency", lambda r: r.with_frequency("1M")),
        ("limit_amt", lambda r: r.with_limit_amt(100)),
        ("tot_limit_amt", lambda r: r.with_tot_limit_amt(100)),
        ("is_limit_amt_fixed", lambda r: r.with_limit_amt_fixed(False)),
    ],
)
def test_model_o_rejects_limits(field: str, setter: Callable[[RecurringRegistration], object]) -> None:
    registration = RecurringRegistration.create("Abonament", RecurringRegistration.MODEL_O, TERMS)
    setter(registration)
    with pytest.raises(DPayValueError, match=f"{field} is not allowed in recurring model O"):
        registration.to_api()


def test_model_o_allows_the_dates() -> None:
    data = (
        RecurringRegistration.create("Abonament", RecurringRegistration.MODEL_O, TERMS)
        .with_expiration_date("2027-09-30")
        .with_init_date("2026-11-01")
        .to_api()
    )
    assert data["expiration_date"] == "2027-09-30"
    assert data["init_date"] == "2026-11-01"


def test_model_a_requires_the_full_terms() -> None:
    registration = (
        RecurringRegistration.create("Abonament", RecurringRegistration.MODEL_A, TERMS)
        .with_frequency("1M")
        .with_limit_amt(5999)
        .with_tot_limit_amt(71988)
        .with_expiration_date("2027-09-30")
        .with_init_date("2026-11-01")
    )
    assert list(registration.to_api()) == [
        "label",
        "model",
        "frequency",
        "limit_amt",
        "tot_limit_amt",
        "expiration_date",
        "init_date",
        "terms_url",
    ]

    incomplete = (
        RecurringRegistration.create("Abonament", RecurringRegistration.MODEL_A, TERMS)
        .with_frequency("1M")
        .with_limit_amt(5999)
        .with_tot_limit_amt(71988)
        .with_expiration_date("2027-09-30")
    )
    with pytest.raises(DPayValueError, match="init_date is required in recurring model A"):
        incomplete.to_api()


def test_model_a_requires_a_fixed_amount() -> None:
    registration = (
        RecurringRegistration.create("Abonament", RecurringRegistration.MODEL_A, TERMS)
        .with_frequency("1M")
        .with_limit_amt(5999)
        .with_tot_limit_amt(71988)
        .with_expiration_date("2027-09-30")
        .with_init_date("2026-11-01")
    )
    assert registration.with_limit_amt_fixed(True).to_api()["is_limit_amt_fixed"] is True
    with pytest.raises(DPayValueError, match="requires a fixed amount"):
        registration.with_limit_amt_fixed(False).to_api()


def test_model_m_keeps_the_key_order_of_every_field() -> None:
    data = (
        RecurringRegistration.create("Subskrypcja", RecurringRegistration.MODEL_M, TERMS)
        .with_terms_version("v1")
        .with_methods(["blik"])
        .with_init_date("2026-08-01")
        .with_expiration_date("2027-01-01")
        .with_limit_amt_fixed(True)
        .with_tot_limit_amt(500000)
        .with_limit_amt(100000)
        .with_frequency("12M")
        .with_alias("SUB-1")
        .to_api()
    )
    assert list(data) == [
        "label",
        "alias",
        "model",
        "frequency",
        "limit_amt",
        "tot_limit_amt",
        "is_limit_amt_fixed",
        "expiration_date",
        "init_date",
        "methods",
        "terms_url",
        "terms_version",
    ]


@pytest.mark.parametrize("frequency", ["1Q", "0M", "1000D", "1m", "M", "12", "1M\n", "\uff11M"])
def test_frequency_follows_the_blik_format(frequency: str) -> None:
    registration = RecurringRegistration.create("Abonament", RecurringRegistration.MODEL_M, TERMS)
    with pytest.raises(DPayValueError, match="Invalid recurring frequency"):
        registration.with_frequency(frequency)


@pytest.mark.parametrize("frequency", ["1D", "14D", "2W", "1M", "999Y"])
def test_frequency_accepts_days_weeks_months_and_years(frequency: str) -> None:
    registration = RecurringRegistration.create("Abonament", RecurringRegistration.MODEL_M, TERMS)
    assert registration.with_frequency(frequency).frequency == frequency


@pytest.mark.parametrize("terms_url", ["not a url", "", "https://", "https://shop.example/" + "x" * 2030])
def test_terms_url_is_required_and_valid(terms_url: str) -> None:
    with pytest.raises(DPayValueError, match="Invalid terms URL"):
        RecurringRegistration.create("Abonament", RecurringRegistration.MODEL_O, terms_url)


def test_label_model_and_alias_are_validated() -> None:
    with pytest.raises(DPayValueError, match="Recurring payment label must be 1-50 characters"):
        RecurringRegistration.create("x" * 51, RecurringRegistration.MODEL_O, TERMS)
    with pytest.raises(DPayValueError, match='Invalid recurring model "Q"'):
        RecurringRegistration.create("Abonament", "Q", TERMS)
    registration = RecurringRegistration.create("Ż" * 50, RecurringRegistration.MODEL_O, TERMS)
    with pytest.raises(DPayValueError, match="Recurring alias must be 1-128 characters"):
        registration.with_alias("")
    # 128 bytes like PHP strlen - a two-byte character counts twice
    registration.with_alias("a" * 128)
    with pytest.raises(DPayValueError, match="Recurring alias must be 1-128 characters"):
        registration.with_alias("ż" * 65)
    with pytest.raises(DPayValueError, match="Terms version must be 1-64 characters"):
        registration.with_terms_version("v" * 65)


@pytest.mark.parametrize("methods", [[], ["blik", "blik"], "blik"])
def test_methods_must_be_a_distinct_non_empty_list(methods: list[str]) -> None:
    registration = RecurringRegistration.create("Abonament", RecurringRegistration.MODEL_O, TERMS)
    with pytest.raises(DPayValueError, match="non-empty list of distinct methods"):
        registration.with_methods(methods)


def test_only_blik_is_a_recurring_method_today() -> None:
    registration = RecurringRegistration.create("Abonament", RecurringRegistration.MODEL_O, TERMS)
    with pytest.raises(DPayValueError, match='Unsupported recurring method "card"'):
        registration.with_methods(["blik", "card"])


@pytest.mark.parametrize("amount", [0, -1, True, 10.5])
def test_limits_are_positive_minor_units(amount: int) -> None:
    registration = RecurringRegistration.create("Abonament", RecurringRegistration.MODEL_M, TERMS)
    with pytest.raises(DPayValueError, match="limit_amt must be at least 1"):
        registration.with_limit_amt(amount)
    with pytest.raises(DPayValueError, match="tot_limit_amt must be at least 1"):
        registration.with_tot_limit_amt(amount)


def test_dates_must_be_iso() -> None:
    registration = RecurringRegistration.create("Abonament", RecurringRegistration.MODEL_M, TERMS)
    with pytest.raises(DPayValueError, match="must be in YYYY-MM-DD format"):
        registration.with_expiration_date("30-09-2027")
    with pytest.raises(DPayValueError, match="must be in YYYY-MM-DD format"):
        registration.with_init_date("2026/11/01")


# Registration and charges through payments.register()


def test_registration_sends_the_object_with_the_blik_code_without_ipn(
    vectors_client: DPayClient, transport: MockHttpClient
) -> None:
    transport.queue_json(
        200,
        {
            "error": False,
            "msg": "Internal processing",
            "status": True,
            "transactionId": "TX-REG",
            "additionalInfo": {"recurring_registration": {"alias": "SUB-0001", "methods": ["blik"]}},
        },
    )
    payment = vectors_client.payments.register(
        RegisterPaymentRequest.create(Money.pln(0), TransactionType.TRANSFERS, _urls(None))
        .with_blik_code("777123", "Mozilla/5.0", "83.238.17.42")
        .with_recurring_registration(_registration())
    )

    body = transport.last_request_body
    assert "url_ipn" not in body
    assert "register_blik_recurring_alias" not in body
    assert body["recurring_registration"] == {
        "label": "Abonament",
        "alias": "SUB-0001",
        "model": "O",
        "terms_url": TERMS,
    }
    assert body["blik_code"] == "777123"
    # Without IPN: empty last segment, a registration has no alias in the checksum
    assert body["checksum"] == _checksum("register_recurring_value_0_without_ipn")
    assert payment.is_internal_processing
    assert payment.recurring_alias == "SUB-0001"
    assert payment.recurring_methods == ["blik"]


def test_charge_binds_the_alias_in_the_checksum(
    vectors_client: DPayClient, transport: MockHttpClient
) -> None:
    transport.queue_json(
        200, {"error": False, "msg": "Internal processing", "status": True, "transactionId": "TX"}
    )
    vectors_client.payments.register(
        RegisterPaymentRequest.create(Money.pln(4999), TransactionType.TRANSFERS, _urls())
        .with_recurring_alias("SUB-0001")
        .with_description("Abonament 10/2026")
    )

    body = transport.last_request_body
    assert body["recurring_alias"] == "SUB-0001"
    assert "user_ip" not in body
    # sha256(service|hash|value|url_success|url_fail|url_ipn|recurring_alias)
    assert body["checksum"] == _checksum("recurring_charge")


def test_charge_without_ipn_keeps_the_empty_segment(
    vectors_client: DPayClient, transport: MockHttpClient
) -> None:
    transport.queue_json(
        200, {"error": False, "msg": "Internal processing", "status": True, "transactionId": "TX"}
    )
    vectors_client.payments.register(
        RegisterPaymentRequest.create(Money.pln(4999), TransactionType.TRANSFERS, _urls(None))
        .with_recurring_alias("SUB-0001")
        .with_client_context("Mozilla/5.0", "83.238.17.42")
    )

    body = transport.last_request_body
    assert body["user_agent"] == "Mozilla/5.0"
    assert body["user_ip"] == "83.238.17.42"
    assert body["checksum"] == _checksum("recurring_charge_without_ipn")


def test_webhook_and_reference_stay_out_of_the_checksum(
    vectors_client: DPayClient, transport: MockHttpClient
) -> None:
    transport.queue_json(
        200, {"error": False, "msg": "https://secure.dpay.pl/transfer@pay@TX", "transactionId": "TX"}
    )
    vectors_client.payments.register(
        RegisterPaymentRequest.create(Money.pln(1000), TransactionType.TRANSFERS, _urls())
        .with_webhook(
            WebhookTarget.create("https://shop.example/webhooks", ["payment.succeeded", "payment.failed"])
        )
        .with_reference("  order-1234 ")
    )

    body = transport.last_request_body
    assert body["webhook"] == {
        "url": "https://shop.example/webhooks",
        "events": ["payment.succeeded", "payment.failed"],
    }
    assert body["reference"] == "order-1234"
    assert list(body)[-3:] == ["webhook", "reference", "checksum"]
    assert body["checksum"] == _checksum("register_with_ipn")


def test_registration_without_blik_code_is_rejected_before_sending() -> None:
    request = RegisterPaymentRequest.create(
        Money.pln(0), TransactionType.TRANSFERS, _urls()
    ).with_recurring_registration(_registration())
    with pytest.raises(DPayValueError, match="BLIK code"):
        request.to_api("sdk-test-service")


@pytest.mark.parametrize(
    ("request_", "message"),
    [
        (
            RegisterPaymentRequest.create(Money.pln(4999), TransactionType.TRANSFERS, _urls())
            .with_blik_code("777123", "Mozilla/5.0", "83.238.17.42")
            .with_recurring_alias("SUB-0001"),
            "blik_code cannot be combined with a recurring payment",
        ),
        (
            RegisterPaymentRequest.create(
                Money.pln(0), TransactionType.TRANSFERS, _urls()
            ).with_recurring_alias("SUB-0001"),
            "A recurring charge requires an amount above 0",
        ),
        (
            RegisterPaymentRequest.create(
                Money.pln(4999), TransactionType.CARD_RECURRING, _urls()
            ).with_recurring_alias("SUB-0001"),
            'Recurring payments require transactionType "transfers"',
        ),
        (
            RegisterPaymentRequest.create(Money.pln(4999), TransactionType.TRANSFERS, _urls())
            .with_recurring_alias("SUB-0001")
            .with_recurring_registration(_registration()),
            "recurring_registration cannot be combined with recurring_alias",
        ),
        (
            RegisterPaymentRequest.create(Money.pln(0), TransactionType.TRANSFERS, _urls())
            .with_blik_code("777123", "Mozilla/5.0", "83.238.17.42")
            .with_channel("86")
            .with_recurring_registration(_registration()),
            "channel cannot be combined with a recurring payment",
        ),
        (
            RegisterPaymentRequest.create(Money.pln(0), TransactionType.TRANSFERS, _urls())
            .with_blik_code("777123", "Mozilla/5.0", "83.238.17.42")
            .with_register_blik_alias(BlikAliasRegistration("OneClick"))
            .with_recurring_registration(_registration()),
            "register_blik_alias cannot be combined with a recurring payment",
        ),
        (
            RegisterPaymentRequest.create(Money.pln(4999), TransactionType.TRANSFERS, _urls())
            .with_card_recurring(CardRecurringRegistration.create("Mandat"))
            .with_recurring_alias("SUB-0001"),
            "register_card_recurring cannot be combined with a recurring payment",
        ),
        (
            RegisterPaymentRequest.create(Money.pln(4999), TransactionType.TRANSFERS, _urls())
            .with_card_recurring_alias("card-1")
            .with_recurring_alias("SUB-0001"),
            "card_recurring_alias cannot be combined with a recurring payment",
        ),
    ],
)
def test_invalid_combinations_are_rejected_before_sending(
    request_: RegisterPaymentRequest, message: str
) -> None:
    with pytest.raises(DPayValueError, match=message):
        request_.to_api("sdk-test-service")


def test_a_channel_does_not_block_a_recurring_charge() -> None:
    body = (
        RegisterPaymentRequest.create(Money.pln(4999), TransactionType.TRANSFERS, _urls())
        .with_channel("86")
        .with_recurring_alias("SUB-0001")
        .to_api("s")
    )
    assert body["channel"] == "86"


def test_blik_alias_is_exclusive_with_recurring_payments() -> None:
    charge = RegisterPaymentRequest.create(
        Money.pln(4999), TransactionType.TRANSFERS, _urls()
    ).with_recurring_alias("SUB-0001")
    with pytest.raises(DPayValueError, match="blik_alias cannot be combined"):
        charge.with_blik_alias("DPAY.UID.1.abcd1234", "Mozilla/5.0", "83.238.17.42")

    registration = RegisterPaymentRequest.create(
        Money.pln(0), TransactionType.TRANSFERS, _urls()
    ).with_recurring_registration(_registration())
    with pytest.raises(DPayValueError, match="recurring payments"):
        registration.with_blik_alias("DPAY.UID.1.abcd1234", "Mozilla/5.0", "83.238.17.42")


def test_recurring_alias_is_1_to_128_bytes() -> None:
    request = RegisterPaymentRequest.create(Money.pln(4999), TransactionType.TRANSFERS, _urls())
    with pytest.raises(DPayValueError, match="Recurring alias must be 1-128 characters"):
        request.with_recurring_alias("")
    with pytest.raises(DPayValueError, match="Recurring alias must be 1-128 characters"):
        request.with_recurring_alias("x" * 129)
    assert request.with_recurring_alias("x" * 128).recurring_alias == "x" * 128


@pytest.mark.parametrize("ip", ["83.238.17.42", "2001:db8::1", "::1"])
def test_client_context_accepts_ipv4_and_ipv6(ip: str) -> None:
    request = RegisterPaymentRequest.create(Money.pln(4999), TransactionType.TRANSFERS, _urls())
    assert request.with_client_context("Mozilla/5.0", ip).user_ip == ip


@pytest.mark.parametrize("ip", ["", "localhost", "256.1.1.1", "010.0.0.1", "fe80::1%eth0", " 10.0.0.1"])
def test_client_context_validates_the_ip(ip: str) -> None:
    request = RegisterPaymentRequest.create(Money.pln(4999), TransactionType.TRANSFERS, _urls())
    with pytest.raises(DPayValueError, match="Invalid user IP"):
        request.with_client_context("Mozilla/5.0", ip)


@pytest.mark.parametrize("reference", ["", "   ", "x" * 65, "order\x01", "a\x7fb", "line\nbreak"])
def test_reference_is_1_to_64_characters_without_control_characters(reference: str) -> None:
    request = RegisterPaymentRequest.create(Money.pln(1000), TransactionType.TRANSFERS, _urls())
    with pytest.raises(DPayValueError, match="Reference must be 1-64 characters without control characters"):
        request.with_reference(reference)


def test_reference_counts_characters_and_is_trimmed_like_the_api() -> None:
    request = RegisterPaymentRequest.create(Money.pln(1000), TransactionType.TRANSFERS, _urls())
    assert request.with_reference("\t" + "ż" * 64 + "\n ").reference == "ż" * 64


# RecurringService


def test_status_returns_the_alias_and_terms(vectors_client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(
        200,
        {
            "status": "success",
            "data": {
                "alias": "SUB-0001",
                "method": "blik",
                "status": "ACTIVE",
                "expiration_date": "2027-09-30",
                "registration": {
                    "transaction_id": TRANSACTION_ID,
                    "label": "Abonament",
                    "model": "A",
                    "frequency": "1M",
                    "limit_amt": 5999,
                    "tot_limit_amt": 71988,
                    "is_limit_amt_fixed": True,
                    "init_date": "2026-11-01",
                    "terms_url": TERMS,
                    "terms_version": "2026-09",
                    "registered_at": "2026-09-26T12:00:00+02:00",
                },
            },
        },
    )

    status = vectors_client.recurring.status("SUB-0001")

    assert transport.last_request.url == "https://api-payments.dpay.pl/api/v1_0/payments/recurring/status"
    assert transport.last_request_body == {
        "service": "sdk-test-service",
        "alias": "SUB-0001",
        "checksum": _checksum("recurring_status"),
    }
    assert status.is_active
    assert status.alias == "SUB-0001"
    assert status.method == "blik"
    assert status.expiration_date == "2027-09-30"
    registration = status.registration
    assert registration is not None
    assert registration.transaction_id == TRANSACTION_ID
    assert registration.limit_amt == 5999
    assert registration.tot_limit_amt == 71988
    assert registration.is_limit_amt_fixed is True
    assert registration.terms_url == TERMS
    assert registration.terms_version == "2026-09"
    assert registration.registered_at == "2026-09-26T12:00:00+02:00"


def test_status_limits_parse_digit_strings_only() -> None:
    registration = RecurringStatus.from_api(
        {"registration": {"limit_amt": "100", "tot_limit_amt": "1.5", "is_limit_amt_fixed": "true"}}
    ).registration
    assert registration is not None
    assert registration.limit_amt == 100
    assert registration.tot_limit_amt is None
    assert registration.is_limit_amt_fixed is None
    for value in ("", "-5", "٣", "12\n", True, 3.0):
        info = RecurringStatus.from_api({"registration": {"limit_amt": value}}).registration
        assert info is not None and info.limit_amt is None


def test_status_without_registration(vectors_client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(
        200, {"status": "success", "data": {"alias": "SUB-0001", "status": None, "registration": None}}
    )
    status = vectors_client.recurring.status("SUB-0001")
    assert not status.is_active
    assert status.status is None
    assert status.registration is None


def test_cancel_signs_the_operation(vectors_client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(200, {"status": "success", "data": {"alias": "SUB-0001", "status": "UNREGISTERED"}})

    status = vectors_client.recurring.cancel("SUB-0001", "Rezygnacja")

    assert status == RecurringStatus.UNREGISTERED
    assert transport.last_request.url == "https://api-payments.dpay.pl/api/v1_0/payments/recurring/cancel"
    assert transport.last_request_body == {
        "service": "sdk-test-service",
        "alias": "SUB-0001",
        "reason": "Rezygnacja",
        # sha256(service|hash|alias|cancel) - a status checksum cannot cancel
        "checksum": _checksum("recurring_cancel"),
    }


def test_cancel_without_reason_defaults_the_status(
    vectors_client: DPayClient, transport: MockHttpClient
) -> None:
    transport.queue_json(200, {"status": "success", "data": []})
    assert vectors_client.recurring.cancel("SUB-0001") == "UNREGISTERED"
    assert list(transport.last_request_body) == ["service", "alias", "checksum"]
    assert transport.last_request_body["checksum"] == _checksum("recurring_cancel")


def test_retry_returns_the_pending_retry(vectors_client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(
        200,
        {
            "status": "success",
            "data": {"transactionId": TRANSACTION_ID, "retry": {"status": "pending", "count": 1}},
        },
    )

    result = vectors_client.recurring.retry(TRANSACTION_ID)

    assert transport.last_request.url == "https://api-payments.dpay.pl/api/v1_0/payments/recurring/retry"
    assert transport.last_request_body == {
        "service": "sdk-test-service",
        "transaction_id": TRANSACTION_ID,
        "checksum": _checksum("recurring_retry"),
    }
    assert result.is_pending
    assert not result.is_failed
    assert result.count == 1
    assert result.transaction_id == TRANSACTION_ID


def test_retry_declined_at_once_is_a_result_not_an_error(
    vectors_client: DPayClient, transport: MockHttpClient
) -> None:
    transport.queue_json(
        200,
        {
            "status": "success",
            "data": {
                "transactionId": TRANSACTION_ID,
                "retry": {
                    "status": "failed",
                    "count": 2,
                    "error": "INSUFFICIENT_FUNDS",
                    "error_description": "IssId: 1",
                },
            },
        },
    )

    result = vectors_client.recurring.retry(TRANSACTION_ID)

    assert result.is_failed
    assert result.error_code == "INSUFFICIENT_FUNDS"
    assert result.error_description == "IssId: 1"


def test_retry_not_allowed_carries_the_reason(vectors_client: DPayClient, transport: MockHttpClient) -> None:
    transport.queue_json(
        400,
        {
            "status": "failed",
            "message": "Recurring charge cannot be retried (DECLINE_NOT_RETRYABLE).",
            "errors": {"retry": "DECLINE_NOT_RETRYABLE", "decline_reason": "SEC_DECLINED"},
        },
    )

    with pytest.raises(InvalidRequestError) as error:
        vectors_client.recurring.retry(TRANSACTION_ID)

    assert error.value.http_status == 400
    assert error.value.field_errors["retry"] == ["DECLINE_NOT_RETRYABLE"]
    assert error.value.field_errors["decline_reason"] == ["SEC_DECLINED"]


def test_status_checksum_matches_the_formula(client: DPayClient, transport: MockHttpClient) -> None:
    from tests.conftest import SECRET, SERVICE

    transport.queue_json(200, {"status": "success", "data": {}})
    client.recurring.status("a-1")
    expected = hashlib.sha256(f"{SERVICE}|{SECRET}|a-1".encode()).hexdigest()
    assert transport.last_request_body["checksum"] == expected
