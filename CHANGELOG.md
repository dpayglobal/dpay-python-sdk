# Changelog

Wszystkie istotne zmiany w tym projekcie są dokumentowane w tym pliku.
Format oparty na [Keep a Changelog](https://keepachangelog.com/pl/1.1.0/),
wersjonowanie zgodne z [SemVer](https://semver.org/lang/pl/).

## [Unreleased]

## [0.3.0] - 2026-11-19

Wersja dogania dokumentację API dpay (OpenAPI 1.6.0) i działa z obecnym API - nie wymaga nowego wydania API.
Port SDK PHP 0.3.0 - parytet potwierdzają golden vectors wygenerowane z SDK PHP 0.3.0 (34 wywołania
i parsowanie odpowiedzi) oraz wspólne `tests/fixtures/api_vectors.json`.

### Breaking

- **BREAKING** `refunds.check_availability()` zwraca `RefundAvailability` (niedostępny) zamiast rzucać wyjątek
  dla każdej odpowiedzi 4xx z kluczem `refund`, w tym 404 (transakcja nie istnieje, wcześniej
  `NotFoundError`) i 423 (zwrot przez BOK dpay). Przyczynę rozróżnia `http_status`. Nadal rzucają:
  401 "Unauthorized request" (`AuthenticationError`), 422, 429 i 5xx.
- **BREAKING** Waluta kwoty trafia do `currency_code`: `Money` w walucie innej niż PLN wysyła `currency_code`
  bez `with_currency_code()` (wcześniej np. `Money.of(49900, "CZK")` rejestrowało 499.00 w walucie domyślnej
  serwisu). `with_currency_code()` i `with_phone_number()` rzucają `DPayValueError`, gdy waluta różni się
  od waluty kwoty - dla MB WAY użyj `Money.of(grosze, Currency.EUR)` zamiast `Money.pln()`. Kwota w PLN
  bez jawnego kodu wysyła body jak dotąd (bez `currency_code`).
- **BREAKING** `IpnVerifier.construct_event()` przyjmuje IPN `alias_update` (wcześniej rzucał
  `SignatureVerificationError` "Invalid IPN payload"). Przychodzi on na `url_ipn`, gdy rejestracja nie miała
  `alias_ipn_url` - obsługa, która oznacza zamówienie jako opłacone bez sprawdzenia `is_transfer`, potraktowałaby
  zmianę aliasu (np. `ALIAS_DECLINED`) jak wpłatę. Dla `alias_update` `amount` jest puste, a `email`,
  `custom` i `attempt` zwracają `None`/0 (te pola nie są podpisane).

### Added

- IPN `alias_update` (BLIK OneClick i płatności cykliczne): `IpnVerifier.construct_event()` weryfikuje podpis
  `sha256(id + hash + type + version)`, `IpnType.ALIAS_UPDATE`, `IpnEvent.is_alias_update`
  i `IpnEvent.alias_update` (`AliasUpdate` ze stałymi `change_type`, `alias_type` i `alias_status`).
- `CardError` (`code`, `decline_code`, `decline_message`): `CardPaymentError.card_error` z obiektu `error`
  odmowy karty oraz `ApiError.card_error` i `ApiError.transaction_id` z pól `cardError` i `transactionId`
  błędu Payments API (np. odrzucone pobranie na zapisanej karcie).
- `client.payouts.list()` i `iterate()` (`POST /api/v1/pbl/withdraws`, filtry `date_from`, `date_to`,
  `state`, `type`, strony do 200) oraz `details_full()` (`POST /api/v1/pbl/withdraws/details/full`: nagłówek,
  sumy całego rozliczenia i pozycje z `payment_id`, `custom`, `ipksef`, strony do 500); modele `PayoutPage`,
  `PayoutListItem`, `PayoutSettlement`, `SettlementPosition`, `PageMeta`, `PayoutState`, `PayoutType`.
- `PayoutDetails.currency` (z `currency_code`, PLN gdy go brak), `export_date` i `is_paysafecard`.
- `refunds.create()`: opcjonalny argument `message_id` - nagłówek `DigitalPayments-PSP-Message-ID`
  (tytuł przelewu `dpay.pl zwrot {message_id}`, poza sumą kontrolną), stała `RefundService.MESSAGE_ID_HEADER`.
- `RegisteredPayment.multibanco` (`MultibancoReference`: encja, referencja, kwota, ważność)
  i `RegisteredPayment.paid_transaction` (`RegisteredTransaction` z odpowiedzi "Transaction paid", statusy
  pending, paid, captured, canceled); `RegisteredPayment.from_api()` przyjmuje walutę kwoty.
- Typowane obiekty webhooków: `WebhookEvent.payment`, `refund`, `recurring_payment`, `payout`
  (`PaymentObject`, `RefundObject`, `RecurringPaymentObject`, `PayoutObject`), `Failure`,
  `DeclineCode` (22 kody odmów dpay) i `FailureCategory`.
- `RecurringRetryResult.is_success` i `RetryRefusal` (kody `errors.retry` odmowy ponowienia).
- `Transaction.rate`, `minimal_fee`, `permanent_fee` i `urls` (`TransactionUrls`).
- `ApplePayRequest.with_email()` i `CardPaymentResult.apple_pay_merchant_session` (sesja
  ApplePayMerchantSession z `redirectText` odpowiedzi APPLE_PAY_INIT).
- `RateLimitError.reset` (nagłówek `X-RateLimit-Reset`), `Currency.USD` i `Currency.RON`,
  `PayoutPosition.is_valid_polish_iban()`.
- `tests/fixtures/api_vectors.json`: wektory IPN transfer, dcb i alias_update oraz sum list i szczegółów
  wypłat.

### Changed

- Walidacja przed wysłaniem tego, co API i tak odrzuca (422 lub 400):
  - etykieta `register_blik_alias` (`BlikAliasRegistration`) i `recurring_registration`
    (`RecurringRegistration`) do 35 znaków (limit BLIK, wcześniej 50);
  - `mb_way_direct` wymaga kanału (`with_channel("373")`) i `DeviceInfo` z `with_browser_java_enabled()`;
  - kanał bezpośredni wymaga emaila, imienia i nazwiska płatnika oraz `with_accept_tos()`; kanały `tester`,
    `paypal`, `installment` i `paysafecard` są odrzucane; pusty kanał (`""`) jest wysyłany jak dotąd
    i oznacza brak kanału;
  - `phone_number` 9-15 znaków, `alias_ipn_url` do 500 znaków;
  - `efaktura` nie łączy się z `blik_code`, `blik_alias`, `register_blik_alias`, płatnościami cyklicznymi
    ani aliasami kart;
  - `PayoutPosition`: IBAN `PL` + 26 cyfr z poprawną sumą kontrolną mod 97 (spacje i małe litery dozwolone)
    i kwota powyżej 0.
- `ApiError.transaction_id` przeniesione z `PaymentRejectedError` do klasy bazowej (bez zmiany zachowania).

Świadome różnice wobec SDK PHP:

- `payouts.list()` przyjmuje filtry jako słownik (`Mapping`), jak tablica w PHP; filtr z wartością `None`
  jest pomijany, a data, która nie jest `str`, rzuca `DPayValueError` (w PHP `TypeError`); w kliencie
  asynchronicznym `payouts.iterate()` jest asynchronicznym generatorem
- identyfikator zwrotu z końcowym znakiem nowej linii odrzuca komunikat "Refund message ID must be non-empty
  printable ASCII" (w PHP ten sam przypadek kończy się komunikatem "Invalid request header")

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

[Unreleased]: https://github.com/dpayglobal/dpay-python-sdk/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/dpayglobal/dpay-python-sdk/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/dpayglobal/dpay-python-sdk/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/dpayglobal/dpay-python-sdk/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/dpayglobal/dpay-python-sdk/releases/tag/v0.1.0
