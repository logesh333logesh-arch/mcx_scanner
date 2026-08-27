"""
Telegram Notifier
==================
Same pattern as your other scanners: bot token + chat id from env vars
(set as GitHub Actions secrets), requests.post to sendMessage — with
retries + backoff since api.telegram.org occasionally times out on
mobile/flaky connections (same issue seen on Scanner-4).
"""

import os
import time
import requests
import config

MAX_ATTEMPTS = 4
TIMEOUT_SECONDS = 30
RETRY_BACKOFF_SECONDS = 3  # wait grows: 3s, 6s, 9s between attempts


def send_telegram_message(text: str):
    token = os.environ.get(config.TELEGRAM_BOT_TOKEN_ENV)
    chat_id = os.environ.get(config.TELEGRAM_CHAT_ID_ENV)
    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    last_error = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = requests.post(url, data={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }, timeout=TIMEOUT_SECONDS)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt < MAX_ATTEMPTS:
                print(f"[WARN] Telegram send attempt {attempt} failed ({e}), retrying...")
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    print(f"[WARN] Telegram send failed after {MAX_ATTEMPTS} attempts: {last_error}")
    raise last_error


def format_strike_alert(commodity: str, symbol: str, option_type: str, strike: float,
                         day_open_premium: float, current_premium: float, move: float,
                         strike_daily_cpr: str) -> str:
    return (
        f"🔔 <b>{commodity} {option_type} {strike:g}</b>\n"
        f"Move: ₹{move:.2f} (Open ₹{day_open_premium:.2f} → Now ₹{current_premium:.2f})\n"
        f"Strike Daily CPR: {strike_daily_cpr}\n"
    )


def format_spot_cpr_block(commodity: str, weekly_type: str, daily_type: str) -> str:
    return (
        f"📊 <b>{commodity} Spot</b>\n"
        f"Weekly CPR: {weekly_type}\n"
        f"Daily CPR: {daily_type}\n"
    )


def format_volume_alert(commodity: str, spike: dict) -> str:
    return (
        f"📈 <b>{commodity} Volume Spike</b>\n"
        f"Today: {spike['today_volume']:.0f} vs 18-day avg {spike['avg_volume']:.0f} "
        f"({spike['ratio']}x)\n"
        f"Direction: {spike['direction']}\n"
    )
