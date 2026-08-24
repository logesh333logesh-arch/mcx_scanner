"""
CPR Calculator — Pivot Boss classification
============================================
Computes CPR (Pivot, BC, TC) from OHLC and classifies it two ways:

1. Width-based type: Narrow CPR / Wide CPR / Virgin CPR / Normal CPR
   (based on how today's CPR width compares to the recent average width)

2. Relationship-based type: compares TODAY's CPR position against
   YESTERDAY's (or last week's) CPR position — this is the table Logesh
   photographed:
       Higher Value CPR          -> Bullish
       Overlapping Higher Value  -> Moderately Bullish
       Lower Value CPR           -> Bearish
       Overlapping Lower Value   -> Moderately Bearish
       Unchanged Value CPR       -> Sideways / Breakout
       Inside Value CPR          -> Breakout / Strong Trend
       Outside Value CPR         -> Sideways

Both daily and weekly CPR use the same functions — just pass in
daily OHLC series or weekly-resampled OHLC series.
"""

from dataclasses import dataclass
from typing import List, Optional
import config


@dataclass
class CPRLevels:
    pivot: float
    bc: float
    tc: float

    @property
    def width(self) -> float:
        return abs(self.tc - self.bc)


def calculate_cpr(high: float, low: float, close: float) -> CPRLevels:
    """Standard CPR formula. Feed previous period's OHLC to get the CPR
    that applies to the CURRENT period (this is intentional — CPR for
    "today" is always derived from "yesterday's" OHLC)."""
    pivot = (high + low + close) / 3
    bc = (high + low) / 2
    tc = (pivot - bc) + pivot
    return CPRLevels(pivot=pivot, bc=min(bc, tc), tc=max(bc, tc))


def classify_width(today: CPRLevels, recent_widths: List[float]) -> str:
    """Narrow / Wide / Virgin / Normal, based on recent average width."""
    if not recent_widths:
        return "Normal CPR"
    avg_width = sum(recent_widths) / len(recent_widths)
    if avg_width == 0:
        return "Virgin CPR"  # first-ever bar / no history — treat as virgin
    ratio = today.width / avg_width
    if ratio <= config.NARROW_CPR_THRESHOLD_PCT:
        return "Narrow CPR"
    if ratio >= config.WIDE_CPR_THRESHOLD_PCT:
        return "Wide CPR"
    return "Normal CPR"


def classify_relationship(today: CPRLevels, prev: Optional[CPRLevels]) -> str:
    """Compares today's CPR (pivot/bc/tc) against the previous period's
    CPR to produce the Higher/Lower/Overlapping/Inside/Outside Value
    classification, mapped straight to the Tamil table Logesh shared."""
    if prev is None:
        return "Virgin CPR"

    t_lo, t_hi = today.bc, today.tc
    p_lo, p_hi = prev.bc, prev.tc

    fully_above = t_lo > p_hi
    fully_below = t_hi < p_lo
    inside = t_lo >= p_lo and t_hi <= p_hi and not (t_lo == p_lo and t_hi == p_hi)
    outside = t_lo <= p_lo and t_hi >= p_hi and not (t_lo == p_lo and t_hi == p_hi)
    unchanged = t_lo == p_lo and t_hi == p_hi
    overlap_higher = (not fully_above) and (t_hi > p_hi) and (t_lo <= p_hi) and (t_lo > p_lo)
    overlap_lower = (not fully_below) and (t_lo < p_lo) and (t_hi >= p_lo) and (t_hi < p_hi)

    if unchanged:
        return "Unchanged Value CPR (Sideways/Breakout)"
    if fully_above:
        return "Higher Value CPR (Bullish)"
    if fully_below:
        return "Lower Value CPR (Bearish)"
    if inside:
        return "Inside Value CPR (Breakout/Strong Trend)"
    if outside:
        return "Outside Value CPR (Sideways)"
    if overlap_higher:
        return "Overlapping Higher Value CPR (Moderately Bullish)"
    if overlap_lower:
        return "Overlapping Lower Value CPR (Moderately Bearish)"
    return "Normal CPR"


def full_classification(ohlc_series: List[dict]) -> dict:
    """
    ohlc_series: list of dicts sorted oldest->newest, each with
        {'high': float, 'low': float, 'close': float}
    Uses the LAST bar as "today" and the second-last as "yesterday".
    Returns width-type + relationship-type + the raw levels.
    """
    if len(ohlc_series) < 2:
        return {"width_type": "Virgin CPR", "relationship_type": "Virgin CPR", "levels": None}

    today_bar = ohlc_series[-1]
    prev_bar = ohlc_series[-2]

    today_cpr = calculate_cpr(today_bar["high"], today_bar["low"], today_bar["close"])
    prev_cpr = calculate_cpr(prev_bar["high"], prev_bar["low"], prev_bar["close"])

    lookback = ohlc_series[-(config.NARROW_CPR_LOOKBACK_DAYS + 1):-1]
    recent_widths = [
        calculate_cpr(b["high"], b["low"], b["close"]).width for b in lookback
    ]

    return {
        "width_type": classify_width(today_cpr, recent_widths),
        "relationship_type": classify_relationship(today_cpr, prev_cpr),
        "levels": today_cpr,
    }
