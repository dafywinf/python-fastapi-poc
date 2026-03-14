"""E2e test fixtures and hooks."""

from collections.abc import Generator
from typing import Any

import allure
import pytest
from playwright.sync_api import sync_playwright

GRAFANA_URL = "http://localhost:3000"
DASHBOARD_UID = "fastapi-observability"


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[Any]
) -> Generator[None, None, None]:
    """Capture a Grafana dashboard screenshot and attach it to Allure.

    Fires on every outcome (pass or fail) for test_dashboard_panels_return_data
    so the report always includes visual proof of panel state.
    """
    outcome = yield
    report = outcome.get_result()  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType, reportAttributeAccessIssue]

    is_panels_test = item.name == "test_dashboard_panels_return_data"

    if report.when == "call" and is_panels_test:  # pyright: ignore[reportUnknownMemberType]
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            page.goto(f"{GRAFANA_URL}/d/{DASHBOARD_UID}?kiosk=tv&refresh=30s")
            page.wait_for_timeout(3000)
            screenshot = page.screenshot(full_page=True)
            browser.close()

        name = (
            "grafana_dashboard_panels_pass"
            if not report.failed  # pyright: ignore[reportUnknownMemberType]
            else "grafana_dashboard_panels_fail"
        )
        allure.attach(
            screenshot,
            name=name,
            attachment_type=allure.attachment_type.PNG,  # pyright: ignore[reportUnknownMemberType]
        )
