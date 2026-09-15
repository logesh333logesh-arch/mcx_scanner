"""
Price History (rolling reference)
====================================
Replaces the "compare to fixed day-open" model with a rolling one:
each run saves the current premium + timestamp per strike, and the
NEXT run compares against that saved value (whatever the interval
between runs is — e.g. ~5-15 min depending on how often the workflow
fires) instead of the whole day's cumulative move from market open.

This catches an actual spike as it happens instead of lagging behind
a big cumulative move from 9:15 AM that may already be reversing by
the time the fixed-baseline threshold is finally crossed.

The history file is committed back to the repo after each run (same
pattern as Scanner-2's alerted_strikes.json) so the next scheduled
run — a fresh process — can read yesterday's... no, THIS run's saved
prices.
"""

import json
import os
from datetime import datetime, timezone

HISTORY_PATH = "price_history.json"

# If the last saved price for a strike is older than this, treat it as
# stale (e.g. first run of the day, or a big gap after a failed run) and
# just re-seed the reference instead of comparing against ancient data.
MAX_REFERENCE_AGE_MINUTES = 30


def load_history(path: str = HISTORY_PATH) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_history(history: dict, path: str = HISTORY_PATH):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


def get_reference(history: dict, instrument_key: str):
    """
    Returns (reference_price, age_minutes) if a usable (not-too-stale)
    saved price exists for this instrument_key, else None.
    """
    entry = history.get(instrument_key)
    if not entry:
        return None
    try:
        saved_time = datetime.fromisoformat(entry["timestamp"])
        age_minutes = (datetime.now(timezone.utc) - saved_time).total_seconds() / 60
    except (KeyError, ValueError):
        return None
    if age_minutes > MAX_REFERENCE_AGE_MINUTES:
        return None
    return entry["price"], age_minutes


def update_reference(history: dict, instrument_key: str, price: float):
    history[instrument_key] = {
        "price": price,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
