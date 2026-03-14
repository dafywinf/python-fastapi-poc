"""E2e test fixtures and hooks."""

from collections.abc import Generator
from typing import Any

import allure
import httpx
import pytest
from playwright.sync_api import sync_playwright

GRAFANA_URL = "http://localhost:3000"

_SCREENSHOT_TESTS: dict[str, str] = {
    "test_dashboard_panels_return_data": "fastapi-observability",
    "test_loki_dashboard_panels_have_data": "fastapi-loki",
}


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[Any]
) -> Generator[None, None, None]:
    """Capture a Grafana dashboard screenshot and attach it to Allure.

    Fires on every outcome (pass or fail) for any dashboard panels test
    so the report always includes visual proof of panel state.
    """
    outcome = yield
    report = outcome.get_result()  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType, reportAttributeAccessIssue]

    dashboard_uid = _SCREENSHOT_TESTS.get(item.name)

    if report.when == "call" and dashboard_uid is not None:  # pyright: ignore[reportUnknownMemberType]
        # Obtain a real Grafana session cookie via the API so that panel
        # fetch() queries are authorised (basic auth headers are ignored by
        # Grafana 11.x for JS-initiated datasource requests).
        login = httpx.post(
            f"{GRAFANA_URL}/login",
            json={"user": "admin", "password": "admin"},
        )
        session_cookie: str = login.cookies.get("grafana_session") or ""

        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            context.add_cookies(
                [
                    {
                        "name": "grafana_session",
                        "value": session_cookie,
                        "domain": "localhost",
                        "path": "/",
                    }
                ]
            )
            page = context.new_page()
            page.goto(f"{GRAFANA_URL}/d/{dashboard_uid}?kiosk=tv&refresh=30s")
            page.wait_for_timeout(3000)
            screenshot = page.screenshot(full_page=True)
            browser.close()

        outcome_label = (
            "pass"
            if not report.failed  # pyright: ignore[reportUnknownMemberType]
            else "fail"
        )
        allure.attach(
            screenshot,
            name=f"grafana_{dashboard_uid}_{outcome_label}",
            attachment_type=allure.attachment_type.PNG,  # pyright: ignore[reportUnknownMemberType]
        )
