from __future__ import annotations

import asyncio
import socket
import sys
import threading
import time
from collections.abc import Generator

import pytest
import uvicorn

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import Page, sync_playwright

from tests.e2e.conftest import signup_payload

pytestmark = pytest.mark.e2e


@pytest.fixture()
def browser_server(e2e: tuple[object, object]) -> Generator[str, None, None]:
    if sys.platform == "win32":
        pytest.skip(
            "The local Windows sandbox cannot start Uvicorn's asyncio server in a thread; "
            "the CI browser job runs this test on Linux."
        )
    application, _ = e2e
    settings = application.state.e2e_settings
    settings.auth_token_body_enabled = False
    settings.auth_legacy_bearer_enabled = False
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    port = int(listener.getsockname()[1])
    listener.close()
    server = uvicorn.Server(
        uvicorn.Config(application, host="127.0.0.1", port=port, log_level="error")
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
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=5)


def test_browser_cookie_auth_csrf_and_multiple_tabs(browser_server: str) -> None:
    with sync_playwright() as playwright_instance:
        browser = playwright_instance.chromium.launch()
        context = browser.new_context()
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
        assert "creator_access" not in page.evaluate("document.cookie")
        assert "creator_refresh" not in page.evaluate("document.cookie")
        assert "creator_csrf=" in page.evaluate("document.cookie")

        # Passing the origin URL makes Playwright filter cookies by that URL's
        # path (`/`), hiding the scoped session cookies from this inspection.
        cookies = context.cookies()
        access_cookie = next(cookie for cookie in cookies if cookie["name"] == "creator_access")
        refresh_cookie = next(cookie for cookie in cookies if cookie["name"] == "creator_refresh")
        assert access_cookie["httpOnly"] is True
        assert refresh_cookie["httpOnly"] is True
        assert access_cookie["path"] == "/api/v1"
        assert refresh_cookie["path"] == "/api/v1/auth"

        second_page = context.new_page()
        second_page.goto(f"{browser_server}/docs")
        assert (
            second_page.evaluate(
                """async () => (await fetch('/api/v1/users/me', {credentials: 'include'})).status"""
            )
            == 200
        )

        missing_csrf = page.evaluate(
            """async () => (await fetch('/api/v1/auth/logout', {
                method: 'POST', credentials: 'include'
            })).status"""
        )
        assert missing_csrf == 403

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
                return response.status;
            }""",
            csrf,
        )
        assert refresh == 200

        stale_logout = page.evaluate(
            """async (csrf) => (await fetch('/api/v1/auth/logout', {
                method: 'POST', credentials: 'include',
                headers: {'X-CSRF-Token': csrf},
            })).status""",
            csrf,
        )
        assert stale_logout == 403

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
