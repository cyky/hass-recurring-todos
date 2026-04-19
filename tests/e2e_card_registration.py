"""E2E test: verify the Recurring Todos card appears in the Lovelace 'Add card' picker.

Usage (from repo root):
    docker compose up -d
    # wait ~30 s for HA to start
    pip install playwright && playwright install chromium
    python tests/e2e_card_registration.py

The script performs a full fresh-install flow:
  1. Wait for HA to be reachable
  2. Complete the onboarding wizard (creates owner account)
  3. Add the Recurring Todos integration via the Integrations UI
  4. Navigate to a dashboard and open the 'Add card' picker
  5. Assert 'Recurring Todos' is listed
"""

from __future__ import annotations

import asyncio
import time

import requests
from playwright.async_api import async_playwright

HA_URL = "http://localhost:8123"
HA_USER = "admin"
HA_PASS = "testpassword1"
TIMEOUT = 60_000  # ms


def wait_for_ha(timeout: int = 60) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{HA_URL}/api/", timeout=3)
            if r.status_code in (200, 401):
                return
        except requests.ConnectionError:
            pass
        time.sleep(2)
    raise RuntimeError(f"HA not reachable at {HA_URL} after {timeout}s")


async def run() -> None:
    wait_for_ha()
    print("HA is up.")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context()
        page = await ctx.new_page()

        # --- Onboarding ---
        await page.goto(f"{HA_URL}/onboarding.html", wait_until="networkidle", timeout=TIMEOUT)

        # Step 1: Create user
        name_input = page.locator("input[name='name']")
        if await name_input.count() > 0:
            await name_input.fill("Admin")
            await page.locator("input[name='username']").fill(HA_USER)
            await page.locator("input[name='password']").fill(HA_PASS)
            await page.locator("input[name='password_confirm']").fill(HA_PASS)
            await page.locator("mwc-button[type='submit'], button[type='submit']").first.click()
            await page.wait_for_load_state("networkidle", timeout=TIMEOUT)

        # Skip remaining onboarding steps
        for _ in range(5):
            skip = page.locator("mwc-button:has-text('Skip'), button:has-text('Skip')")
            if await skip.count() > 0:
                await skip.first.click()
                await page.wait_for_load_state("networkidle", timeout=TIMEOUT)
            else:
                break

        finish = page.locator("mwc-button:has-text('Finish'), button:has-text('Finish')")
        if await finish.count() > 0:
            await finish.first.click()
            await page.wait_for_load_state("networkidle", timeout=TIMEOUT)

        print("Onboarding complete.")

        # --- Add integration ---
        await page.goto(f"{HA_URL}/config/integrations", wait_until="networkidle", timeout=TIMEOUT)
        await page.locator("mwc-fab, ha-fab, [title='Add integration']").first.click()
        await page.wait_for_selector("ha-integration-search-input, input[placeholder*='Search']", timeout=TIMEOUT)

        search = page.locator("ha-integration-search-input input, input[placeholder*='Search']").first
        await search.fill("Recurring Todos")
        await page.wait_for_timeout(1000)

        result = page.locator(
            "ha-integration-list-item:has-text('Recurring Todos'), mwc-list-item:has-text('Recurring Todos')"
        )
        await result.first.click()
        await page.wait_for_load_state("networkidle", timeout=TIMEOUT)

        # Submit config flow (default name)
        submit = page.locator("mwc-button[dialogaction='submit'], mwc-button:has-text('Submit')")
        if await submit.count() > 0:
            await submit.first.click()
            await page.wait_for_load_state("networkidle", timeout=TIMEOUT)

        print("Integration added.")

        # --- Open Add Card picker ---
        await page.goto(HA_URL, wait_until="networkidle", timeout=TIMEOUT)
        await page.wait_for_timeout(2000)

        # Enter edit mode
        await page.locator("ha-menu-button, [aria-label='Open sidebar']").first.click()
        edit_btn = page.locator("mwc-list-item:has-text('Edit dashboard'), [aria-label*='edit']")
        if await edit_btn.count() > 0:
            await edit_btn.first.click()
        else:
            # Try the kebab menu
            await page.locator("ha-button-menu, [aria-label='More options']").first.click()
            await page.locator("mwc-list-item:has-text('Edit dashboard')").first.click()
        await page.wait_for_timeout(1000)

        # Click Add Card
        await page.locator("ha-fab[label='Add card'], mwc-fab[label='Add card'], [title='Add card']").first.click()
        await page.wait_for_selector("ha-card-picker, hui-card-picker", timeout=TIMEOUT)

        # Search for the card
        picker_search = page.locator("ha-card-picker input, hui-card-picker input, search-input input")
        if await picker_search.count() > 0:
            await picker_search.first.fill("Recurring")
            await page.wait_for_timeout(500)

        content = await page.content()
        assert "Recurring Todos" in content, (
            "FAIL: 'Recurring Todos' not found in Add card picker.\n"
            "The card JS is not being loaded on fresh install."
        )
        print("PASS: 'Recurring Todos' card is visible in the Add card picker.")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(run())
