from __future__ import annotations

import pytest

from dpay import Config, DPayClient, DPayValueError
from dpay._internal.base_urls import BaseUrls
from dpay.testing import MockHttpClient


def test_requires_service() -> None:
    with pytest.raises(DPayValueError, match='Option "service" is required'):
        Config.from_dict({"secret_hash": "x"})


def test_requires_secret_hash() -> None:
    with pytest.raises(DPayValueError, match='Option "secret_hash" is required'):
        Config.from_dict({"service": "x"})


def test_rejects_empty_service() -> None:
    with pytest.raises(DPayValueError, match='Option "service" is required'):
        Config.from_dict({"service": "", "secret_hash": "x"})


def test_unknown_option_is_reported_first() -> None:
    with pytest.raises(DPayValueError, match='Unknown option "retries"'):
        Config.from_dict({"retries": 3})


def test_timeout_defaults_to_30() -> None:
    assert Config.from_dict({"service": "s", "secret_hash": "h"}).timeout == 30


def test_explicit_none_behaves_like_missing_key() -> None:
    assert Config.from_dict({"service": "s", "secret_hash": "h", "timeout": None}).timeout == 30


def test_timeout_must_be_positive_int() -> None:
    for value in (0, -1, "30", 1.5, True):
        with pytest.raises(DPayValueError, match='Option "timeout" must be a positive integer'):
            Config.from_dict({"service": "s", "secret_hash": "h", "timeout": value})


def test_http_client_must_expose_request() -> None:
    with pytest.raises(DPayValueError, match='Option "http_client" must implement HttpClient'):
        Config.from_dict({"service": "s", "secret_hash": "h", "http_client": object()})


def test_base_urls_must_be_mapping() -> None:
    with pytest.raises(DPayValueError, match='Option "base_urls" must be a mapping'):
        Config.from_dict({"service": "s", "secret_hash": "h", "base_urls": ["x"]})


def test_base_urls_values_must_be_non_empty_strings() -> None:
    with pytest.raises(DPayValueError, match="Base URLs must be non-empty strings"):
        Config.from_dict({"service": "s", "secret_hash": "h", "base_urls": {"panel": ""}})


def test_base_urls_rejects_unknown_host() -> None:
    with pytest.raises(DPayValueError, match='Unknown base URL key "shop"'):
        Config.from_dict({"service": "s", "secret_hash": "h", "base_urls": {"shop": "https://x"}})


def test_base_urls_strip_all_trailing_slashes() -> None:
    config = Config.from_dict({"service": "s", "secret_hash": "h", "base_urls": {"panel": "https://x///"}})
    assert config.base_urls.resolve(BaseUrls.PANEL) == "https://x"


def test_base_urls_defaults() -> None:
    urls = BaseUrls()
    assert urls.resolve(BaseUrls.API_PAYMENTS) == "https://api-payments.dpay.pl"
    assert urls.resolve(BaseUrls.PANEL) == "https://panel.dpay.pl"
    assert urls.resolve(BaseUrls.GATEWAY) == "https://secure.dpay.pl"


def test_resolve_rejects_unknown_host() -> None:
    with pytest.raises(DPayValueError, match='Unknown API host "nope"'):
        BaseUrls().resolve("nope")


def test_client_exposes_all_services() -> None:
    client = DPayClient(service="s", secret_hash="h", http_client=MockHttpClient())
    for name in ("payments", "refunds", "banks", "blik", "cards", "payouts"):
        assert getattr(client, name) is not None


def test_client_rejects_bad_config_before_building_services() -> None:
    with pytest.raises(DPayValueError):
        DPayClient(service="", secret_hash="h")


def test_client_reports_unknown_keyword() -> None:
    with pytest.raises(DPayValueError, match='Unknown option "retries"'):
        DPayClient(service="s", secret_hash="h", retries=3)
