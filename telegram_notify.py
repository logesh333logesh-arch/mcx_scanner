"""
Telegram Notifier
==================
Same pattern as your other scanners: bot token + chat id from env vars
(set as GitHub Actions secrets), plain requests.post to sendMessage.
"""

import os
import requests
import config


def send_telegram_message(text: str):
    token = os.environ.get(config.TELEGRAM_BOT_TOKEN_ENV)
    chat_id = os.environ.get(config.TELEGRAM_CHAT_ID_ENV)
    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, data={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }, timeout=15)
    resp.raise_for_status()
    return resp.json()


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
  
