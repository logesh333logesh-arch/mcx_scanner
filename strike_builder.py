"""
Strike Builder
==============
Given the day's OPENING spot price of a commodity, picks:
    - 10 OTM CE strikes (above spot)
    - 10 OTM PE strikes (below spot)

Strikes are matched against the actual Upstox instrument master CSV
(not just computed from strike_step) so we only ever alert on strikes
that genuinely exist / are tradeable for the current monthly expiry.
"""

import csv
from dataclasses import dataclass
from typing import List
import config


@dataclass
class OptionInstrument:
    instrument_key: str
    trading_symbol: str
    strike: float
    option_type: str   # "CE" or "PE"
    expiry: str         # ISO date string


def load_instrument_master(path: str = config.INSTRUMENT_MASTER_PATH) -> List[dict]:
    """
    Loads the Upstox instrument master CSV.
    Download fresh daily from: https://assets.upstox.com/market-quote/instruments/exchange/MCX.csv.gz
    Expected columns (Upstox format): instrument_key, tradingsymbol, name,
    strike, option_type, expiry, ...
    """
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def nearest_expiry(rows: List[dict], instrument_master_name: str, min_strikes: int = 10) -> str:
    """Picks the nearest upcoming monthly expiry for a given commodity's
    instrument-master name (e.g. 'CRUDE OIL', not 'CRUDEOIL').
    Skips expiries with fewer than min_strikes contracts listed — this
    happens when a front-month contract is 1-2 days from expiry and most
    of its strike chain has already gone illiquid/delisted, which would
    otherwise get wrongly picked as "nearest"."""
    from collections import Counter
    counts = Counter(
        r["expiry"] for r in rows
        if r.get("name", "").upper() == instrument_master_name.upper() and r.get("expiry")
    )
    expiries = sorted(e for e, c in counts.items() if c >= min_strikes)
    if not expiries:
        raise ValueError(f"No expiries with sufficient strikes found for {instrument_master_name}")
    return expiries[0]


def build_strikes(commodity_key: str, day_open_spot: float,
                   instrument_rows: List[dict]) -> List[OptionInstrument]:
    """
    Returns 10 OTM CE + 10 OTM PE OptionInstrument objects for the
    nearest monthly expiry, centered on day_open_spot.
    commodity_key is the config.py key (e.g. 'CRUDEOIL') — this function
    looks up the actual instrument-master name to match against, and
    filters by tradingsymbol prefix since standard-lot and mini-lot
    contracts often share the same 'name' field (e.g. CRUDEOIL vs
    CRUDEOILM both appear under name='CRUDE OIL').
    """
    cfg = config.COMMODITIES[commodity_key]
    instrument_master_name = cfg["instrument_master_name"]
    ts_prefix = cfg["tradingsymbol_prefix"]
    ts_exclude_prefix = cfg.get("tradingsymbol_exclude_prefix")
    expiry = nearest_expiry(instrument_rows, instrument_master_name)

    calls, puts = [], []
    for r in instrument_rows:
        if r.get("name", "").upper() != instrument_master_name.upper():
            continue
        if r.get("expiry") != expiry:
            continue
        tsym = r.get("tradingsymbol", "").upper()
        if not tsym.startswith(ts_prefix.upper()):
            continue
        if ts_exclude_prefix and tsym.startswith(ts_exclude_prefix.upper()) and ts_prefix.upper() != ts_exclude_prefix.upper():
            continue
        opt_type = r.get("option_type", "").upper()
        try:
            strike = float(r.get("strike", 0))
        except ValueError:
            continue
        if opt_type == "CE" and strike > day_open_spot:
            calls.append((strike, r))
        elif opt_type == "PE" and strike < day_open_spot:
            puts.append((strike, r))

    # OTM CE: 10 closest strikes ABOVE spot (ascending)
    calls.sort(key=lambda x: x[0])
    otm_calls = calls[:config.STRIKES_PER_SIDE]

    # OTM PE: 10 closest strikes BELOW spot (descending -> closest first)
    puts.sort(key=lambda x: x[0], reverse=True)
    otm_puts = puts[:config.STRIKES_PER_SIDE]

    result = []
    for strike, r in otm_calls + otm_puts:
        result.append(OptionInstrument(
            instrument_key=r["instrument_key"],
            trading_symbol=r["tradingsymbol"],
            strike=strike,
            option_type=r["option_type"].upper(),
            expiry=expiry,
        ))
    return result
