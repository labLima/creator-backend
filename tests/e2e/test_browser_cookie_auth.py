from __future__ import annotations

import asyncio
import socket
import sys
import threading
import time
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from ipaddress import IPv4Address
from pathlib import Path

import pytest
import uvicorn
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import Page, sync_playwright

from tests.e2e.conftest import signup_payload

pytestmark = pytest.mark.e2e


def _write_test_certificate(directory: Path) -> tuple[Path, Path]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(UTC) - timedelta(minutes=1))
        .not_valid_after(datetime.now(UTC) + timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(IPv4Address("127.0.0.1"))]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    key_path = directory / "browser-test-key.pem"
    certificate_path = directory / "browser-test-cert.pem"
    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    certificate_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    return certificate_path, key_path


@pytest.fixture()
def browser_server(e2e: tuple[object, object], tmp_path: Path) -> Generator[str, None, None]:
    if sys.platform == "win32":
        pytest.skip(
            "The local Windows sandbox cannot start Uvicorn's asyncio server in a thread; "
            "the CI browser job runs this test on Linux."
        )
    application, _ = e2e
    settings = application.state.e2e_settings
    settings.auth_token_body_enabled = False
    settings.auth_legacy_bearer_enabled = False
    settings.auth_cookie_secure = True
    certificate, key = _write_test_certificate(tmp_path)
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    port = int(listener.getsockname()[1])
    listener.close()
    server = uvicorn.Server(
        uvicorn.Config(
            application,
            host="127.0.0.1",
            port=port,
            log_level="error",
            ssl_certfile=str(certificate),
            ssl_keyfile=str(key),
        )
    )

    def run_server() -> None:
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        server.run()

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.05)
    if not server.started:
        server.should_exit = True
        thread.join(timeout=2)
        pytest.fail("uvicorn did not start")
    try:
        yield f"https://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=5)


def test_browser_cookie_auth_csrf_and_multiple_tabs(browser_server: str) -> None:
    with sync_playwright() as playwright_instance:
        browser = playwright_instance.chromium.launch()
        context = browser.new_context(ignore_https_errors=True)
        page: Page = context.new_page()
        page.goto(f"{browser_server}/docs")

        signup = page.evaluate(
            """async ({payload}) => {
                const response = await fetch('/api/v1/auth/signup', {
                    method: 'POST', credentials: 'include',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload),
                });
                return {status: response.status, body: await response.json()};
            }""",
            {"payload": signup_payload("browser@example.com")},
        )
        assert signup["status"] == 201
        assert "access_token" not in signup["body"]["data"]["session"]
        assert "refresh_token" not in signup["body"]["data"]["session"]

        cookies = {cookie["name"]: cookie for cookie in context.cookies()}
        access_cookie = cookies["creator_access"]
        refresh_cookie = cookies["creator_refresh"]
        csrf_cookie = cookies["creator_csrf"]
        assert (access_cookie["httpOnly"], access_cookie["secure"]) == (True, True)
        assert (access_cookie["sameSite"], access_cookie["path"]) == ("Lax", "/api/v1")
        assert (refresh_cookie["httpOnly"], refresh_cookie["secure"]) == (True, True)
        assert (refresh_cookie["sameSite"], refresh_cookie["path"]) == (
            "Strict",
            "/api/v1/auth",
        )
        assert (csrf_cookie["httpOnly"], csrf_cookie["secure"]) == (False, True)
        assert (csrf_cookie["sameSite"], csrf_cookie["path"]) == ("Lax", "/")

        # Navigate into both session-cookie paths before checking JavaScript visibility.
        page.goto(f"{browser_server}/api/v1/auth/csrf")
        visible_cookies = page.evaluate("document.cookie")
        assert "creator_access" not in visible_cookies
        assert "creator_refresh" not in visible_cookies
        assert "creator_csrf=" in visible_cookies

        login = page.evaluate(
            """async () => {
                const response = await fetch('/api/v1/auth/login', {
                    method: 'POST', credentials: 'include',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        email: 'browser@example.com', password: 'correct-password'
                    }),
                });
                return {status: response.status, body: await response.json()};
            }"""
        )
        assert login["status"] == 200
        assert "access_token" not in login["body"]["data"]
        assert "refresh_token" not in login["body"]["data"]

        page.reload()
        assert (
            page.evaluate(
                """async () => (await fetch('/api/v1/users/me', {credentials: 'include'})).status"""
            )
            == 200
        )

        second_page = context.new_page()
        second_page.goto(f"{browser_server}/api/v1/auth/csrf")
        assert (
            second_page.evaluate(
                """async () => (await fetch('/api/v1/users/me', {credentials: 'include'})).status"""
            )
            == 200
        )

        missing_refresh_csrf = page.evaluate(
            """async () => (await fetch('/api/v1/auth/refresh', {
                method: 'POST', credentials: 'include'
            })).status"""
        )
        missing_logout_csrf = page.evaluate(
            """async () => (await fetch('/api/v1/auth/logout', {
                method: 'POST', credentials: 'include'
            })).status"""
        )
        assert missing_refresh_csrf == missing_logout_csrf == 403

        csrf = page.evaluate(
            """document.cookie.split('; ').find(value => value.startsWith('creator_csrf='))
                .split('=').slice(1).join('=')"""
        )
        refresh = page.evaluate(
            """async (csrf) => {
                const response = await fetch('/api/v1/auth/refresh', {
                    method: 'POST', credentials: 'include',
                    headers: {'X-CSRF-Token': csrf},
                });
                return {status: response.status, body: await response.json()};
            }""",
            csrf,
        )
        assert refresh["status"] == 200
        assert "access_token" not in refresh["body"]["data"]
        assert "refresh_token" not in refresh["body"]["data"]

        refreshed_csrf = page.evaluate(
            """document.cookie.split('; ').find(value => value.startsWith('creator_csrf='))
                .split('=').slice(1).join('=')"""
        )
        assert refreshed_csrf != csrf
        logout = page.evaluate(
            """async (csrf) => (await fetch('/api/v1/auth/logout', {
                method: 'POST', credentials: 'include',
                headers: {'X-CSRF-Token': csrf},
            })).status""",
            refreshed_csrf,
        )
        assert logout == 200
        assert (
            second_page.evaluate(
                """async () => (await fetch('/api/v1/users/me', {credentials: 'include'})).status"""
            )
            == 401
        )
        browser.close()
