from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import pytest

from dpay import ApiRequest, ApiResponse, DPayClient, TransportError
from dpay.http import UrllibHttpClient
from dpay.http.httpx_client import HttpxAsyncHttpClient


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self._respond(200, {"ok": True})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        if self.path.startswith("/error"):
            self._respond(422, {"errors": {"value": ["wymagane"]}})
            return
        self._respond(200, {"echo": json.loads(body) if body else None})

    def _respond(self, status: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Custom-Header", "yes")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args: Any) -> None:
        return


@pytest.fixture(scope="module")
def server() -> Any:
    httpd = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()


def test_response_headers_are_lowercased() -> None:
    response = ApiResponse(200, {"Content-Type": "application/json"}, "{}")
    assert response.headers == {"content-type": "application/json"}
    assert response.get_header("CONTENT-TYPE") == "application/json"
    assert response.get_header("missing") is None


def test_decode_json_returns_none_for_scalars() -> None:
    assert ApiResponse(200, {}, '"text"').decode_json() is None
    assert ApiResponse(200, {}, "5").decode_json() is None
    assert ApiResponse(200, {}, "broken").decode_json() is None
    assert ApiResponse(200, {}, "{}").decode_json() == {}
    assert ApiResponse(200, {}, "[]").decode_json() == []


def test_api_request_is_frozen() -> None:
    request = ApiRequest("GET", "https://a.pl")
    with pytest.raises(AttributeError):
        request.method = "POST"  # type: ignore[misc]


def test_urllib_client_performs_a_real_get(server: str) -> None:
    response = UrllibHttpClient(timeout=5).request(ApiRequest("GET", f"{server}/ping"))
    assert response.status == 200
    assert response.decode_json() == {"ok": True}
    assert response.get_header("x-custom-header") == "yes"


def test_urllib_client_sends_body_and_headers(server: str) -> None:
    request = ApiRequest(
        "POST",
        f"{server}/echo",
        {"Content-Type": "application/json", "User-Agent": "test-agent"},
        '{"a":1}',
    )
    response = UrllibHttpClient(timeout=5).request(request)
    assert response.decode_json() == {"echo": {"a": 1}}


def test_urllib_client_returns_error_responses_instead_of_raising(server: str) -> None:
    response = UrllibHttpClient(timeout=5).request(
        ApiRequest("POST", f"{server}/error", {"Content-Type": "application/json"}, "{}")
    )
    assert response.status == 422
    assert response.decode_json() == {"errors": {"value": ["wymagane"]}}


def test_urllib_client_maps_network_failure_to_transport_error() -> None:
    client = UrllibHttpClient(timeout=1)
    with pytest.raises(TransportError):
        client.request(ApiRequest("GET", "http://127.0.0.1:1/nope"))


def test_client_end_to_end_against_local_server(server: str) -> None:
    dpay = DPayClient(
        service="s",
        secret_hash="h",
        timeout=5,
        base_urls={"panel": server, "api_payments": server},
    )
    transaction = dpay.payments.details("tx-1")
    assert transaction.raw == {"echo": transaction.raw["echo"]}


def test_client_surfaces_api_errors_end_to_end(server: str) -> None:
    from dpay import InvalidRequestError

    dpay = DPayClient(service="s", secret_hash="h", timeout=5, base_urls={"panel": f"{server}/error"})
    with pytest.raises(InvalidRequestError) as error:
        dpay.payments.details("tx-1")
    assert error.value.field_errors == {"value": ["wymagane"]}


async def test_httpx_client_works_against_local_server(server: str) -> None:
    client = HttpxAsyncHttpClient(timeout=5)
    try:
        response = await client.request(ApiRequest("GET", f"{server}/ping"))
        assert response.status == 200
        assert response.decode_json() == {"ok": True}
    finally:
        await client.aclose()


async def test_httpx_client_maps_network_failure() -> None:
    client = HttpxAsyncHttpClient(timeout=1)
    try:
        with pytest.raises(TransportError):
            await client.request(ApiRequest("GET", "http://127.0.0.1:1/nope"))
    finally:
        await client.aclose()
