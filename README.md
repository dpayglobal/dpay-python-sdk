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

## Klient asynchroniczny

Identyczne API, metody korutynowe:

```python
from dpay.aio import AsyncDPayClient

async with AsyncDPayClient(service="nazwa_serwisu", secret_hash="twoj_secret_hash") as dpay:
    payment = await dpay.payments.register(request)
    transaction = await dpay.payments.details(payment.transaction_id)
```

## Obsługa IPN

dpay.pl uznaje IPN za dostarczony wyłącznie, gdy body odpowiedzi to dokładnie `OK`.
Kod HTTP nie jest sprawdzany. Zawsze weryfikuj kwotę z własnym zamówieniem.

```python
from dpay import IpnEvent, IpnVerifier, SignatureVerificationError

def ipn_view(request):
    try:
        event = IpnVerifier.construct_event(request.body, "twoj_secret_hash")
    except SignatureVerificationError:
        return HttpResponse("Invalid signature", status=400)

    if event.is_transfer or event.is_capture:
        mark_order_as_paid(event.id, event.amount)

    return HttpResponse(IpnEvent.ACK)
```

`event.amount` to surowy string dziesiętny - payload IPN nie niesie waluty,
więc porównaj go z kwotą własnego zamówienia.

## Zwroty

```python
from dpay import Money

dpay.refunds.create("identyfikator-transakcji")
dpay.refunds.create("identyfikator-transakcji", Money.pln(500), "reklamacja")

availability = dpay.refunds.check_availability("identyfikator-transakcji")
if availability.is_available:
    ...
```

## Szczegóły transakcji i banki

```python
transaction = dpay.payments.details("identyfikator-transakcji")
transaction.is_paid
transaction.available_refund_amount.to_decimal()
transaction.refunds

banks = dpay.banks.for_service()
```

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

## Obsługa błędów

Wszystkie wyjątki SDK dziedziczą po `DPayError`.

```python
from dpay import ApiError, DPayError, InvalidRequestError, TransportError

try:
    payment = dpay.payments.register(request)
except InvalidRequestError as error:
    error.field_errors
except ApiError as error:
    error.http_status
    error.error_code
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
| `SignatureVerificationError` | niepoprawny podpis IPN |
| `TransportError` | awaria sieci |
| `DPayValueError` | niepoprawny argument (dziedziczy też po `ValueError`) |

## Konfiguracja

| Opcja | Typ | Opis |
|---|---|---|
| `service` | `str` | Nazwa Punktu Płatności z panel.dpay.pl (wymagane) |
| `secret_hash` | `str` | Klucz Secret Hash (wymagane) |
| `timeout` | `int` | Timeout HTTP w sekundach (domyślnie 30) |
| `http_client` | `HttpClient` | Własny transport (proxy, retry, testy) |
| `base_urls` | `dict[str, str]` | Nadpisanie hostów API |

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
    