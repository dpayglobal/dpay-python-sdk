# Changelog

Wszystkie istotne zmiany w tym projekcie są dokumentowane w tym pliku.
Format oparty na [Keep a Changelog](https://keepachangelog.com/pl/1.1.0/),
wersjonowanie zgodne z [SemVer](https://semver.org/lang/pl/).

## [Unreleased]

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

- `cards.capture()` przyjmuje opcjonalną kwotę, zgodnie z kontraktem OpenAPI
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

[Unreleased]: https://github.com/dpayglobal/dpay-python-sdk/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/dpayglobal/dpay-python-sdk/releases/tag/v0.1.0
