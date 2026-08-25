"""
Upstox Data Fetcher
====================
Thin wrapper around the Upstox v2 REST API for:
    - spot (underlying MCX index) daily & weekly OHLC history
    - option instrument OHLC history (for CPR on premium)
    - live/day-open quotes for the selected strikes

NOTE: Upstox does not do fully automated headless login (TOTP-based
manual login step required daily, same as your Scanner-4 setup).
This module assumes UPSTOX_ACCESS_TOKEN is already generated and
available as an environment variable / GitHub Actions secret before
this script runs — reuse your existing manual_login.py from Scanner-4.
"""

import os
import requests
import config
import manual_login

BASE_URL = "https://api.upstox.com/v2"


def _headers():
    # Prefer token.txt (written by manual_login.py, same as Scanner-4).
    # Falls back to env var in case you wire it differently in CI.
    try:
        token = manual_login.load_token()
    except FileNotFoundError:
        token = os.environ.get(config.UPSTOX_ACCESS_TOKEN_ENV)

    if not token:
        raise RuntimeError(
            "No Upstox access token found — run manual_login.py first "
            f"(or set {config.UPSTOX_ACCESS_TOKEN_ENV})."
        )
    return {"Accept": "application/json", "Authorization": f"Bearer {token}"}


def get_historical_ohlc(instrument_key: str, interval: str, from_date: str, to_date: str):
    """
    interval: 'day' or 'week'
    dates: 'YYYY-MM-DD'
    Returns list of {date, open, high, low, close, volume} oldest->newest.
    """
    url = f"{BASE_URL}/historical-candle/{instrument_key}/{interval}/{to_date}/{from_date}"
    resp = requests.get(url, headers=_headers(), timeout=15)
    resp.raise_for_status()
    candles = resp.json().get("data", {}).get("candles", [])
    # Upstox returns newest->oldest; each candle: [ts, open, high, low, close, volume, oi]
    parsed = [
        {"date": c[0], "open": c[1], "high": c[2], "low": c[3], "close": c[4], "volume": c[5]}
        for c in reversed(candles)
    ]
    return parsed


def get_day_open_price(instrument_key: str) -> float:
    """Live quote's day-open price for spot or a specific option strike."""
    url = f"{BASE_URL}/market-quote/quotes"
    resp = requests.get(url, headers=_headers(), params={"instrument_key": instrument_key}, timeout=15)
    resp.raise_for_status()
    data = resp.json().get("data", {})
    key = next(iter(data), None)
    if not key:
        raise RuntimeError(f"No quote data returned for {instrument_key}")
    return float(data[key]["ohlc"]["open"])


def get_live_ltp(instrument_key: str) -> float:
    url = f"{BASE_URL}/market-quote/ltp"
    resp = requests.get(url, headers=_headers(), params={"instrument_key": instrument_key}, timeout=15)
    resp.raise_for_status()
    data = resp.json().get("data", {})
    key = next(iter(data), None)
    if not key:
        raise RuntimeError(f"No LTP data returned for {instrument_key}")
    return float(data[key]["last_price"])
  
