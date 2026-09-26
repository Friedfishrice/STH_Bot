import os
import time
from playwright.sync_api import sync_playwright
import requests

# Target configuration
PRODUCT_URL = "https://blinkit.com/prn/x/prid/1404276"  # Replace with actual product URL
CHECK_INTERVAL_SECONDS = 10  # 5 minutes

# Set dark store coordinates (e.g. your delivery location)
LATITUDE = 12.8988
LONGITUDE = 77.5323

# Telegram Bot Credentials (optional - set as env vars or replace directly)
TELEGRAM_BOT_TOKEN = os.getenv("8308862718:AAEnWouMwTz5eYMzpukzEBfLAYju5eqyjts")
TELEGRAM_CHAT_ID = os.getenv("2065486159")


def send_alert(message: str):
  """Sends an instant alert via Telegram Bot."""
  if "YOUR_BOT_TOKEN" in TELEGRAM_BOT_TOKEN:
    print(f"[ALERT] {message}")
    return
  url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
  payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
  try:
    requests.post(url, json=payload, timeout=10)
  except Exception as e:
    print(f"Failed to send alert: {e}")


def check_stock_status():
  with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    # Emulate browser context with exact geolocation permissions
    context = browser.new_context(
        geolocation={"latitude": LATITUDE, "longitude": LONGITUDE},
        permissions=["geolocation"],
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
    )
    page = context.new_page()

    try:
      page.goto(PRODUCT_URL, wait_until="domcontentloaded", timeout=60000)
      page.wait_for_timeout(5000)  # Wait 5 seconds for React components to render 

      # Scan page content for stock indicators
      body_text = page.locator("body").inner_text().lower()

      # Blinkit UI indicators:
      # Out of stock/Coming soon items typically display "out of stock", "coming soon", or "sold out"
      is_unavailable = any(
          phrase in body_text
          for phrase in [
              "out of stock",
              "coming soon",
              "currently unavailable",
              "sold out",
          ]
      )

      # Check if actionable "ADD" or "Add to Cart" button exists and is enabled
      add_button = page.locator(
          'button:has-text("ADD"), div:has-text("ADD")'
      ).first

      if not is_unavailable and add_button.is_visible():
        print(f"[{time.strftime('%X')}] IN STOCK!")
        send_alert(
            f"🚨 *HOT WHEELS IN STOCK!* 🚨\n\nLink: {PRODUCT_URL}\nCheck out immediately!"
        )
        return True
      else:
        print(
            f"[{time.strftime('%X')}] Item still unavailable (Out of stock /"
            " Coming soon)."
        )
        return False

    except Exception as err:
      print(f"[{time.strftime('%X')}] Encountered an error: {err}")
      return False
    finally:
      browser.close()


def run_monitor():
  print("Starting Blinkit stock tracker (every 5 minutes)...")
  while True:
    in_stock = check_stock_status()
    if in_stock:
      break
    time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
  run_monitor()