import asyncio, os
from playwright.async_api import async_playwright

BASE = "https://pharmacy-mgmt-portal.preview.emergentagent.com"
OUT = "/app/backend/static/manual_screens"
os.makedirs(OUT, exist_ok=True)

PAGES = [
    ("dashboard", "/dashboard"),
    ("ventes", "/sales"),
    ("produits", "/products"),
    ("approvisionnements", "/supplies"),
    ("clients", "/customers"),
    ("fournisseurs", "/suppliers"),
    ("dettes", "/debts"),
    ("solde_fournisseurs", "/supplier-debts"),
    ("shifts", "/shifts"),
    ("planification", "/shift-schedules"),
    ("rapports", "/reports"),
    ("inventaire", "/inventory"),
    ("mouvements_stock", "/stock-movements"),
    ("pertes_stock", "/stock-losses"),
    ("codes_promo", "/promo-codes"),
    ("parametres", "/settings"),
]

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page.goto(f"{BASE}/login", wait_until="networkidle")
        await page.screenshot(path=f"{OUT}/login.png")
        await page.fill('[data-testid="email-input"]', "admin@pharmaflow.com")
        await page.fill('[data-testid="password-input"]', "admin123")
        await page.click('[data-testid="login-submit-button"]')
        await page.wait_for_url("**/dashboard", timeout=20000)
        await page.wait_for_timeout(3000)
        for name, path in PAGES:
            try:
                await page.goto(f"{BASE}{path}", wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(2500)
                for _ in range(2):
                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(400)
                await page.screenshot(path=f"{OUT}/{name}.png")
                print(f"OK {name}")
            except Exception as e:
                print(f"FAIL {name}: {e}")
        await browser.close()

asyncio.run(main())
