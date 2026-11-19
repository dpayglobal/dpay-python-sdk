# dpay Python SDK

Oficjalna biblioteka Pythona do integracji z API płatności [dpay.pl](https://dpay.pl).

## Wymagania

- Python 3.10 lub nowszy
- Brak zależności runtime dla klienta synchronicznego

## Instalacja

```bash
pip install dpay-python-sdk
```

Klient asynchroniczny wymaga dodatkowej zależności:

```bash
pip install "dpay-python-sdk[async]"
```

> **Uwaga na nazwę pakietu.** Instalujesz `dpay-python-sdk`, a importujesz `dpay`.
> Nie instaluj pakietu o nazwie `dpay` z PyPI - to niepowiązany projekt, który
> zajmuje ten sam moduł najwyższego poziomu i przykryłby to SDK.

## Szybki start

```python
from dpay import DPayClient, Money, RegisterPaymentRequest, ReturnUrls, TransactionType

dpay = DPayClient(service="nazwa_serwisu", secret_hash="twoj_secret_hash")

payment = dpay.payments.register(
    RegisterPaymentRequest.create(
        Money.pln(1050),
        TransactionType.TRANSFERS,
        ReturnUrls(
            "https://twojsklep.pl/sukces",
            "https://twojsklep.pl/blad",
            "https://twojsklep.pl/ipn",
        ),
    )
    .with_description("Zamówienie #1234")
    .with_custom("order-1234")
)

if payment.redirect_url is not None:
    return redirect(payment.redirect_url)
```

## Waluta

Waluta płatności to waluta kwoty `Money`. Kwota w innej walucie niż PLN wysyła `currency_code` sama
(od 0.3.0), np. CZK dla banków czeskich, EUR dla MB WAY, Multibanco i banków słowackich. Serwis musi mieć
tę walutę włączoną (PLN, EUR, CZK, USD, RON).

```python
from dpay import Currency

RegisterPaymentRequest.create(Money.of(49900, Currency.CZK), TransactionType.TRANSFERS, urls)
```

`with_currency_code()` i `with_phone_number()` przyjmują tylko walutę kwoty - `Money.pln()` z kodem `EUR`
rzuca `DPayValueError`.

## MB WAY i kanały bezpośrednie

Kanał bezpośredni (`with_channel()`) wymaga emaila, imienia i nazwiska płatnika oraz `with_accept_tos()`.
MB WAY wymaga dodatkowo kanału `373` i pełnego `DeviceInfo` z `with_browser_java_enabled()` - SDK sprawdza
to przed wysłaniem (API odpowiedziałoby 422).

```python
from dpay import Currency, DeviceInfo, Payer

payment = dpay.payments.register(
    RegisterPaymentRequest.create(Money.of(1250, Currency.EUR), TransactionType.MB_WAY_DIRECT, urls)
    .with_phone_number("+351912345678", Currency.EUR)
    .with_channel("373")
    .with_payer(Payer.create().with_email("cliente@example.pt").with_name("Joao", "Silva"))
    .with_accept_tos(True)
    .with_device_info(
        DeviceInfo.create(
            accept, "pt-PT", 24, 1080, 1920, 0, user_agent, "Win32", "38.72,-9.14", device_id, "Netscape"
        ).with_browser_java_enabled(False)
    )
)
```

Multibanco (kanał `390`, EUR) zwraca referencję do pokazania płatnikowi:

```python
reference = payment.multibanco  # entity, reference, amount, expires_at
```

Odpowiedź "Transaction paid" (płatność już opłacona) niesie transakcję w `payment.paid_transaction`.

## Klient asynchroniczny

Identyczne API, metody korutynowe:

```python
from dpay.aio import AsyncDPayClient

async with AsyncDPayClient(service="nazwa_serwisu", secret_hash="twoj_secret_hash") as dpay:
    payment = await dpay.payments.register(request)
    transaction = await dpay.payments.details(payment.transaction_id)
```

## Płatności cykliczne

Rejestracja idzie razem z płatnością kodem BLIK klienta (kwota `0` - sama zgoda, więcej - opłata inicjalna).
Kolejne obciążenia wysyła Twój serwer, bez kodu.

```python
from dpay import Money, RecurringRegistration, RegisterPaymentRequest, ReturnUrls, TransactionType

urls = ReturnUrls("https://twojsklep.pl/sukces", "https://twojsklep.pl/blad")

registration = dpay.payments.register(
    RegisterPaymentRequest.create(Money.pln(0), TransactionType.TRANSFERS, urls)
    .with_blik_code(kod_blik, request.headers["User-Agent"], adres_ip_klienta)
    .with_recurring_registration(
        RecurringRegistration.create(
            "Abonament Premium", RecurringRegistration.MODEL_O, "https://twojsklep.pl/regulamin"
        ).with_alias("SUB-1234")
    )
)

charge = dpay.payments.register(
    RegisterPaymentRequest.create(Money.pln(4999), TransactionType.TRANSFERS, urls)
    .with_recurring_alias("SUB-1234")
    .with_description("Abonament Premium 10/2026")
)

status = dpay.recurring.status("SUB-1234")           # ACTIVE, INACTIVE, UNREGISTERED, EXPIRED, DECLINED
retry = dpay.recurring.retry(charge.transaction_id)  # po odmowie, np. INSUFFICIENT_FUNDS
dpay.recurring.cancel("SUB-1234", "Rezygnacja klienta")
```

Obciążenie wiąże alias z sumą kontrolną, a anulowanie ma własną sumę - SDK liczy obie.
Limity API: `status` do 60, `retry` i `cancel` do 30 zapytań na minutę (licznik wspólny z resztą API
płatności z tego adresu IP) - nie odpytuj statusu w pętli, wynik przychodzi webhookiem.
Odmowę ponowienia opisuje `error.field_errors["retry"]` (stałe `RetryRefusal`).
Zmiany statusu płatności cyklicznej przychodzą też jako IPN `alias_update` (patrz Obsługa IPN).

## Webhooki

Zdarzenia (`payment.succeeded`, `refund.failed`, `recurring_payment.canceled` i inne) są podpisane.
Weryfikuj je na surowym body, przed parsowaniem JSON:

```python
from dpay import PaymentObject, SignatureVerificationError, WebhookVerifier

def webhook_view(request):
    try:
        event = WebhookVerifier.construct_event(
            request.body,     # surowe bajty żądania
            request.headers,  # dowolny mapping, wielkość liter nazw nie ma znaczenia
            "whsec_...",      # sekret endpointu z panelu; w czasie rotacji lista sekretów
        )
    except SignatureVerificationError:
        return HttpResponse(status=400)

    payment = event.payment  # PaymentObject, None dla innych obiektów
    if payment is not None and payment.status == PaymentObject.STATUS_SUCCEEDED:
        mark_order_as_paid(payment.merchant_reference, payment.amount)  # Money, grosze + waluta
    failure = payment.failure if payment is not None else None
    if failure is not None and failure.is_retryable:
        ...  # np. DeclineCode.INSUFFICIENT_FUNDS - klient może zapłacić ponownie
    return HttpResponse(status=200)
```

Obiekty: `event.payment`, `event.refund`, `event.recurring_payment`, `event.payout`; surowy słownik -
`event.object`.

Deduplikuj zdarzenia po `event.id`. Historię zdarzeń (np. po awarii endpointu) pobierzesz przez
`dpay.events.iterate(types=["payment.succeeded"])`.

Własny adres zdarzeń jednej płatności: `.with_webhook(WebhookTarget.create("https://twojsklep.pl/webhooks"))`
(podpisywany sekretem webhooków serwisu).

## Obsługa IPN

IPN przychodzi tylko wtedy, gdy podasz adres IPN w `ReturnUrls` (IPN `alias_update` także na
`with_alias_ipn_url()`).

dpay.pl uznaje IPN za dostarczony wyłącznie, gdy body odpowiedzi to dokładnie `OK`.
Kod HTTP nie jest sprawdzany. Zawsze weryfikuj kwotę z własnym zamówieniem.

```python
from dpay import IpnEvent, IpnVerifier, SignatureVerificationError

def ipn_view(request):
    try:
        event = IpnVerifier.construct_event(request.body, "twoj_secret_hash")
    except SignatureVerificationError:
        return HttpResponse("Invalid signature", status=400)

    if event.is_transfer:
        mark_order_as_paid(event.id, event.amount)
    elif event.is_alias_update:
        alias = event.alias_update  # change_type, alias_type, alias_status, ...

    return HttpResponse(IpnEvent.ACK)
```

IPN `alias_update` (zmiana aliasu BLIK OneClick lub płatności cyklicznej) przychodzi na
`with_alias_ipn_url()`, a bez niego na adres IPN. Ma inny podpis (`sha256(id + hash + type + version)`) -
`construct_event()` rozpoznaje go po `type`, więc zawsze sprawdzaj typ (`event.is_transfer`) przed
oznaczeniem zamówienia jako opłaconego: `event.id` to wtedy płatność, która zarejestrowała alias,
a `event.amount` jest puste. Podpis nie obejmuje pól aliasu (`event.alias_update`) - przed reakcją na zmianę
potwierdź stan przez `dpay.recurring.status()` lub `dpay.blik.alias()`.

`event.amount` to surowy string dziesiętny - payload IPN nie niesie waluty,
więc porównaj go z kwotą własnego zamówienia.

## Zwroty

```python
from dpay import Money, WebhookTarget

dpay.refunds.create("identyfikator-transakcji")
dpay.refunds.create("identyfikator-transakcji", Money.pln(500), "reklamacja")

# Odpowiedź oznacza przyjęcie zwrotu - wynik przychodzi zdarzeniem refund.succeeded / refund.failed
dpay.refunds.create(
    "identyfikator-transakcji",
    Money.pln(500),
    webhook=WebhookTarget.create(
        "https://twojsklep.pl/webhooks/zwroty", ["refund.succeeded", "refund.failed"]
    ),
)

# Własny identyfikator zwrotu (nagłówek DigitalPayments-PSP-Message-ID) - tytuł przelewu "dpay.pl zwrot RET-1234"
dpay.refunds.create("identyfikator-transakcji", Money.pln(500), message_id="RET-1234")

availability = dpay.refunds.check_availability("identyfikator-transakcji")
if availability.is_available:
    ...
```

`check_availability()` zwraca wynik (nie wyjątek) dla każdej odmowy biznesowej z kluczem `refund`: 400, 402,
404 (transakcja nie istnieje), 406, 409, 410, 411, 423 i biznesowego 401 - przyczynę rozróżnia
`availability.http_status`. Błędna suma kontrolna (401 "Unauthorized request"), 422, 429 i 5xx rzucają
wyjątek.

## Szczegóły transakcji i banki

```python
transaction = dpay.payments.details("identyfikator-transakcji")
transaction.is_paid
transaction.available_refund_amount.to_decimal()
transaction.refunds

transaction.rate  # prowizja, np. "1.49"
transaction.urls  # TransactionUrls: success, fail, ipn

banks = dpay.banks.for_service()
```

## Wypłaty

```python
from dpay import PayoutState

for payout in dpay.payouts.iterate({"date_from": "2026-08-01", "state": PayoutState.PROCESSED}):
    settlement = dpay.payouts.details_full(payout.id)
    for position in settlement.positions:
        position.payment_id  # transakcja z IPN, custom, net, fee, gross
```

`list()` zwraca jedną stronę (`per_page` do 200), `details_full()` - sumy całego rozliczenia
(`summary_net`, `summary_count`) i stronę pozycji (`per_page` do 500).

## Karty S2S

```python
from dpay import CardData, CardEncryptor, CardPaymentRequest, DeviceInfo

public_key = dpay.cards.public_key()
encrypted = CardEncryptor().encrypt(
    CardData("4111111111111111", "123", "12/28"),
    transaction_id,
    public_key,
)

result = dpay.cards.pay_otp(
    transaction_id,
    CardPaymentRequest.create(device_info).with_encrypted_card_data(encrypted),
)

if result.requires_three_ds_form:
    return HttpResponse(result.three_ds_form_html)
if result.has_dcc_offer:
    offer = result.dcc_offer
```

Klucz publiczny jest rotowany - pobieraj go przed każdą próbą płatności.

`dpay.cards.capture()` i `dpay.cards.cancel()` wysyłają sumę kontrolną operacji wyliczaną przez SDK;
`capture()` przyjmuje też `WebhookTarget` dla zdarzenia `payment.captured`.

Apple Pay: `ApplePayRequest.init(device_info)` zwraca sesję w `result.apple_pay_merchant_session`
(przekaż ją do `completeMerchantValidation()` na urządzeniu); `ApplePayRequest.pay(...).with_email()`
wysyła email płatnika.

## Obsługa błędów

Wszystkie wyjątki SDK dziedziczą po `DPayError`.

```python
from dpay import ApiError, DPayError, InvalidRequestError, RateLimitError, TransportError

try:
    payment = dpay.payments.register(request)
except InvalidRequestError as error:
    error.field_errors
    error.transaction_id  # transakcja utworzona przed błędem, np. odrzucone pobranie z karty
    error.card_error      # CardError: code, decline_code (ISO 8583), decline_message
except RateLimitError as error:
    error.retry_after     # sekundy; error.reset - czas Unix odnowienia limitu
except ApiError as error:
    error.http_status
    error.error_code  # np. CHECKSUM_REQUIRED, WEBHOOK_URL_INVALID
    error.reason      # szczegół obok kodu, np. https_required
except TransportError:
    ...  # błąd sieci - status płatności nieznany, użyj payments.details()
```

| Wyjątek | Kiedy |
|---|---|
| `AuthenticationError` | 401 - niepoprawny checksum |
| `InvalidRequestError` | 400, 422 |
| `AccessDeniedError` | 403 |
| `NotFoundError` | 404 |
| `RateLimitError` | 429 |
| `ApiServerError` | 5xx |
| `PaymentRejectedError` | rejestracja odrzucona przy HTTP 200 |
| `CardPaymentError` | płatność kartą odrzucona przy HTTP 200 |
| `SignatureVerificationError` | niepoprawny podpis IPN albo webhooka |
| `TransportError` | awaria sieci |
| `DPayValueError` | niepoprawny argument (dziedziczy też po `ValueError`) |

Odmowa karty z HTTP 200 (`success: false`) rzuca `CardPaymentError`: `error_code` to komunikat API
(np. `DCC_OFFER_EXPIRED`), a `card_error` - kod odmowy, gdy wystawca go podał.

## Konfiguracja

| Opcja | Typ | Opis |
|---|---|---|
| `service` | `str` | Nazwa Punktu Płatności z panel.dpay.pl (wymagane) |
| `secret_hash` | `str` | Klucz Secret Hash (wymagane) |
| `timeout` | `int` | Timeout HTTP w sekundach (domyślnie 30) |
| `http_client` | `HttpClient` | Własny transport (proxy, retry, testy) |
| `base_urls` | `dict[str, str]` | Nadpisanie hostów API, klucze: `api_payments`, `panel`, `gateway` |

## Testowanie integracji

```python
from dpay import DPayClient
from dpay.testing import MockHttpClient

transport = MockHttpClient()
transport.queue_json(200, {"transactionId": "tx-1", "msg": "https://secure.dpay.pl/pay/1"})

dpay = DPayClient(service="test", secret_hash="test", http_client=transport)
payment = dpay.payments.register(request)

assert transport.last_request_body["value"] == "10.50"
```

## Licencja

Apache-2.0
    