# Changelog

Wszystkie istotne zmiany w tym projekcie są dokumentowane w tym pliku.
Format oparty na [Keep a Changelog](https://keepachangelog.com/pl/1.1.0/),
wersjonowanie zgodne z [SemVer](https://semver.org/lang/pl/).

## [Unreleased]

## [0.2.0] - wydanie razem z wdrożeniem API dpay

Wersja wymaga API dpay z tym samym wydaniem (wspólne API płatności cyklicznych, suma kontrolna capture
i anulowania kart). Zmiany łamiące zgodność są oznaczone jako **BREAKING**. Port SDK PHP 0.2.0 -
parytet potwierdzają golden vectors wygenerowane z SDK PHP 0.2.0.

### Added

- `client.recurring` (`RecurringService`, `AsyncRecurringService`): `status()`, `retry()` i `cancel()`
  płatności cyklicznej (`/api/v1_0/payments/recurring/*`), modele `RecurringStatus`,
  `RecurringRegistrationInfo`, `RecurringRetryResult`.
- `RegisterPaymentRequest.with_recurring_registration(RecurringRegistration)` - rejestracja płatności
  cyklicznej (modele O, A i M, `terms_url` wymagany) z kodem BLIK klienta.
- `RegisterPaymentRequest.with_recurring_alias()` - obciążenie zapisanej płatności cyklicznej bez kodu BLIK;
  alias wchodzi do sumy kontrolnej. `with_client_context()` - opcjonalne IP i przeglądarka klienta
  przy obciążeniu.
- Webhooki: `WebhookVerifier.construct_event()` i `verify()` (Standard Webhooks, podpis `v1`, tolerancja
  czasu, kilka podpisów i sekretów w czasie rotacji), `WebhookEvent`, `WebhookEventType`.
- `client.events` (`EventService`, `AsyncEventService`): historia zdarzeń z filtrami, `list()` i `iterate()`
  po stronach.
- `WebhookTarget` - własny adres zdarzeń w rejestracji płatności (`with_webhook()`), zwrocie
  (`refunds.create(..., webhook=...)`) i capture karty (`cards.capture(..., webhook)`);
  `RegisterPaymentRequest.with_reference()`.
- `ApiError.reason`, `PaymentRejectedError.error_description`, `RegisteredPayment.recurring_alias`
  i `RegisteredPayment.recurring_methods`.
- `tests/fixtures/api_vectors.json` - wspólne wektory sum kontrolnych i podpisów webhooków wszystkich SDK dpay.

### Changed

- **BREAKING** `cards.capture()` i `cards.cancel()` wysyłają `service` i sumę
  `sha256(operacja|service|transaction_id|amount|hash)` - API odrzuca je bez sumy (401).
- **BREAKING** `ReturnUrls`: adres IPN jest opcjonalny (`ipn: str | None = None`); bez niego `url_ipn`
  nie jest wysyłany, a IPN nie przychodzi (wynik przychodzi webhookiem).
- Mapowanie błędów czyta kod błędu z pola `code` (np. `CHECKSUM_REQUIRED`, `WEBHOOK_URL_INVALID`),
  potem z `errorcode`.
- Suma kontrolna API PBL (`ordered_body`) liczona jest z całego body i spłaszcza obiekty zagnieżdżone
  (np. `webhook`) w kolejności wysyłki.

Świadome różnice wobec SDK PHP:

- `events.list()` i `events.iterate()` przyjmują filtry jako argumenty nazwane (`types`, `created_from`,
  `created_to`, `starting_after`, `limit`) zamiast tablicy; w kliencie asynchronicznym `iterate()`
  jest asynchronicznym generatorem
- `WebhookVerifier` przyjmuje surowe body jako `bytes` albo `str`, a nagłówki z dowolnego obiektu
  z metodą `items()` (także nazwy i wartości `bytes` z ASGI)

### Removed

- **BREAKING** `blik.recurring_status()`, `BlikRecurringRegistration`, `BlikRecurringStatus`,
  `BlikRecurringRegistrationInfo` i `RegisterPaymentRequest.with_register_blik_recurring_alias()` - API
  usunęło te endpointy i pole; użyj `client.recurring` i `with_recurring_registration()`.
- **BREAKING** `BlikAliasType.PAYID` (aliasy OneClick są tylko `UID`), `TransactionType.BLIK_RECURRING`
  i `TransactionType.BIZUM_DIRECT` (API odrzuca je kodem 422).

### Deprecated

- `IpnType.CAPTURE`, `IpnEvent.is_capture` i `IpnEvent.capture_payment_id` - dpay nie wysyła już IPN
  typu `capture`; użyj zdarzenia `payment.captured`.

## [0.1.1] - 2026-07-23

### Fixed

- `cards.capture()` ponownie wymaga kwoty. W 0.1.0 argument był opcjonalny w oparciu
  o błędny odczyt kontraktu OpenAPI - kwota jest w tym endpoincie wymagana, a wywołanie
  bez niej wysyłało puste body odrzucane przez API. Sygnatura wraca do zgodności z SDK PHP.

## [0.1.0] - 2026-07-22

Pierwsze wydanie. Port SDK PHP `dpayglobal/dpay-php-sdk` z zachowaniem parytetu
wire-protocol, potwierdzonym golden vectors generowanymi z SDK PHP oraz smoke
testem na produkcyjnym API.

### Added

- Klient synchroniczny `DPayClient` - zero zależności runtime, transport na `urllib`
- Klient asynchroniczny `AsyncDPayClient` w `dpay.aio` - extra `[async]`, transport na `httpx`
- Rejestracja płatności (`payments.register`) z pełną macierzą pól opcjonalnych
- Szczegóły transakcji wraz ze zwrotami (`payments.details`)
- Zwroty pełne i częściowe oraz sprawdzanie dostępności zwrotu (`refunds`)
- Lista banków pay-by-link (`banks`)
- BLIK: aliasy OneClick, wyrejestrowanie, status aliasów Recurring, BLIK Level 0 (`blik`)
- Karty server-to-server: szyfrowanie RSA PKCS#1 v1.5 w czystym Pythonie, płatność
  OTP/3DS, pre-autoryzacja, capture, anulowanie, Google Pay, Apple Pay, DCC (`cards`)
- Szczegóły wypłat 1:1 (`payouts`)
- Weryfikacja podpisów IPN (`IpnVerifier`) z porównaniem odpornym na atak czasowy
- Hierarchia wyjątków z korzeniem `DPayError` i normalizacją błędów API
- Transporty testowe `MockHttpClient` i `MockAsyncHttpClient` w `dpay.testing`
- Znacznik `py.typed` - pełne typowanie sprawdzane przez `mypy --strict`

### Changed

Świadome różnice wobec SDK PHP:

- modele odpowiedzi wystawiają właściwości zamiast metod `get*()`
- `PermissionException` odpowiada `AccessDeniedError`, bo `PermissionError`
  koliduje z wbudowanym wyjątkiem Pythona
- `payouts.details()` rzuca wyjątek zamiast zwrócić obiekt raportujący `id=0`,
  gdy odpowiedź jest kopertą błędu bez pola `id`
- `User-Agent` identyfikuje `dpay-python-sdk`

### Notes

Pakiet nazywa się `dpay-python-sdk`, a moduł importu to `dpay`. Nazwa `dpay`
na PyPI należy do niepowiązanego projektu, który zajmuje ten sam moduł najwyższego
poziomu. Zachowaliśmy krótki import dla spójności z SDK PHP i lepszego DX -
tamten pakiet wymaga zależności ze składnią Pythona 2 i nie da się go zaimportować
na Pythonie 3.10+, więc realne ryzyko współistnienia jest znikome.

[Unreleased]: https://github.com/dpayglobal/dpay-python-sdk/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/dpayglobal/dpay-python-sdk/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/dpayglobal/dpay-python-sdk/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/dpayglobal/dpay-python-sdk/releases/tag/v0.1.0
