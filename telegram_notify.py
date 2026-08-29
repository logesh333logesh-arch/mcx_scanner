"""
Telegram Notifier
==================
Simple premium-spike alert format (Scanner-2 style) — no CPR.
Bot token + chat id from env vars (set as GitHub Actions secrets),
requests.post to sendMessage — with retries + backoff since
api.telegram.org occasionally times out on mobile/flaky connections.
"""

import os
import time
import requests
import config

MAX_ATTEMPTS = 4
TIMEOUT_SECONDS = 30
RETRY_BACKOFF_SECONDS = 3  # wait grows: 3s, 6s, 9s between attempts

OPTION_TYPE_EMOJI = {"CE": "🟢", "PE": "🔴"}
MONEYNESS_EMOJI = {"OTM": "🅾️", "ITM": "ℹ️"}


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


def format_spot_trend(commodity_key: str, day_open_spot: float, current_spot: float) -> str:
    move = current_spot - day_open_spot
    pct = (move / day_open_spot * 100) if day_open_spot else 0
    direction = "💹 UP" if move >= 0 else "🔻 DOWN"
    return f"Spot Trend: {direction} ₹{abs(move):.2f} ({abs(pct):.2f}%)"


def format_strike_alert(commodity_key: str, symbol: str, option_type: str, moneyness: str,
                         strike: float, day_open_premium: float, current_premium: float,
                         move: float, day_open_spot: float, current_spot: float) -> str:
    commodity_emoji = config.COMMODITIES[commodity_key]["emoji"]
    opt_emoji = OPTION_TYPE_EMOJI.get(option_type, "")
    money_emoji = MONEYNESS_EMOJI.get(moneyness, "")
    threshold = config.COMMODITIES[commodity_key]["min_move_rupees"]

    return (
        f"🚨 <b>Premium Spike Alert</b>\n"
        f"Commodity: {commodity_emoji} {commodity_key}\n"
        f"Contract: 📅 MONTHLY\n"
        f"Strike: {strike:g} {opt_emoji} {option_type} ({money_emoji} {moneyness})\n"
        f"{format_spot_trend(commodity_key, day_open_spot, current_spot)}\n"
        f"Opening Premium: ₹{day_open_premium:.2f}\n"
        f"Current Premium: ₹{current_premium:.2f}\n"
        f"Spike: ₹{move:.2f} (Threshold: ₹{threshold})\n"
    )


def format_volume_alert(commodity_key: str, spike: dict) -> str:
    commodity_emoji = config.COMMODITIES[commodity_key]["emoji"]
    return (
        f"📊 <b>Volume Spike Alert</b>\n"
        f"Commodity: {commodity_emoji} {commodity_key}\n"
        f"Today: {spike['today_volume']:.0f} vs 18-day avg {spike['avg_volume']:.0f} "
        f"({spike['ratio']}x)\n"
        f"Direction: {spike['direction']}\n"
    )
  
