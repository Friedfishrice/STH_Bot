import asyncio
import os
import time
from playwright.async_api import async_playwright
import requests

# ---------------------------------------------------------------------------
# TARGET CONFIGURATION
# ---------------------------------------------------------------------------
PRODUCT_URL = "your blinit link"
CHECK_INTERVAL_SECONDS = 10  # How often to check stock (seconds)

# ALERT COOLDOWN CONFIGURATION:
# Change this value to adjust Telegram notification frequency when an item stays in stock.
# Examples: 60 = 1 minute | 300 = 5 minutes | 600 = 10 minutes | 0 = Every check (10s)
ALERT_COOLDOWN_SECONDS = 300

# LOCATIONS TO TRACK (Coordinates)
LOCATIONS = [
    {
        "name": "location 1",
        "latitude": ,
        "longitude": 
    },
    {
        "name": "location 2",
        "latitude": ,
        "longitude": 
    }
]

# ---------------------------------------------------------------------------
# TELEGRAM BOT CREDENTIALS
# ---------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Dictionary to keep track of the last notification timestamp per location
last_alert_times = {loc["name"]: 0 for loc in LOCATIONS}


def send_alert(message: str):
    """Sends an instant alert via Telegram Bot."""
    if not TELEGRAM_BOT_TOKEN or "YOUR_BOT_TOKEN" in TELEGRAM_BOT_TOKEN:
        print(f"[ALERT] {message}")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        res.raise_for_status()
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")


async def check_location_stock(browser, loc_info):
    """Creates a browser context with specific geolocation and checks stock."""
    context = await browser.new_context(
        geolocation={"latitude": loc_info["latitude"], "longitude": loc_info["longitude"]},
        permissions=["geolocation"],
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    )
    
    page = await context.new_page()
    timestamp = time.strftime('%X')
    loc_name = loc_info["name"]
    
    try:
        await page.goto(PRODUCT_URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)  # Wait for React elements to load

        body_text = (await page.locator("body").inner_text()).lower()

        is_unavailable = any(
            phrase in body_text
            for phrase in [
                "out of stock",
                "coming soon",
                "currently unavailable",
                "sold out",
            ]
        )

        add_button = page.locator('button:has-text("ADD"), div:has-text("ADD")').first

        if not is_unavailable and await add_button.is_visible():
            print(f"[{timestamp}] 🚨 IN STOCK at {loc_name}!")
            
            # Check if cooldown duration has passed before sending another Telegram alert
            current_time = time.time()
            if current_time - last_alert_times[loc_name] >= ALERT_COOLDOWN_SECONDS:
                send_alert(
                    f"🚨 *ITEM IN STOCK!* 🚨\n\n"
                    f"*Location:* {loc_name}\n"
                    f"*Link:* {PRODUCT_URL}\n"
                    f"Check out immediately!"
                )
                last_alert_times[loc_name] = current_time
            else:
                print(f"[{timestamp}] Telegram alert suppressed for {loc_name} (cooldown active).")

        else:
            print(f"[{timestamp}] Unavailable at {loc_name}")

    except Exception as err:
        print(f"[{timestamp}] Error checking {loc_name}: {err}")
    finally:
        await context.close()


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        print("Starting continuous multi-location stock tracker...")
        print(f"Checking every {CHECK_INTERVAL_SECONDS}s | Alert cooldown: {ALERT_COOLDOWN_SECONDS}s")
        print("Press Ctrl+C to stop.\n")
        
        while True:
            # Check all locations concurrently in parallel
            tasks = [check_location_stock(browser, loc) for loc in LOCATIONS]
            await asyncio.gather(*tasks)
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTracker stopped by user.")
