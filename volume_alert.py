"""
Volume Spike Alert (Index/Spot level)
=======================================
Compares today's (intraday-so-far) volume against the 18-day average
daily volume. If it spikes, reports whether the spike is happening on
an up-move (buying pressure) or down-move (selling pressure) bar.
"""

from typing import List, Optional
import config


def average_volume(daily_ohlc: List[dict], lookback_days: int = config.VOLUME_AVG_LOOKBACK_DAYS) -> float:
    """daily_ohlc: oldest->newest list of {open, high, low, close, volume}.
    Uses the lookback window EXCLUDING today (today is the last element)."""
    history = daily_ohlc[-(lookback_days + 1):-1]
    if not history:
        return 0.0
    return sum(bar["volume"] for bar in history) / len(history)


def check_volume_spike(daily_ohlc: List[dict]) -> Optional[dict]:
    """
    Returns None if no spike, else a dict describing the spike:
        {avg_volume, today_volume, ratio, direction}
    direction is 'up-move (buying)' or 'down-move (selling)' based on
    whether today's close is above or below today's open so far.
    """
    if len(daily_ohlc) < 2:
        return None

    today = daily_ohlc[-1]
    avg_vol = average_volume(daily_ohlc)
    if avg_vol == 0:
        return None

    ratio = today["volume"] / avg_vol
    if ratio < config.VOLUME_SPIKE_MULTIPLIER:
        return None

    direction = "up-move (buying)" if today["close"] >= today["open"] else "down-move (selling)"
    return {
        "avg_volume": avg_vol,
        "today_volume": today["volume"],
        "ratio": round(ratio, 2),
        "direction": direction,
    }
  
