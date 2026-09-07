"""
Strike Builder
==============
Given the day's OPENING spot price of a commodity, picks:
    - 10 OTM CE strikes (above spot) + 5 ITM CE strikes (below spot)
    - 10 OTM PE strikes (below spot) + 5 ITM PE strikes (above spot)
    -> 15 CE + 15 PE = 30 strikes per commodity

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
    option_type: str    # "CE" or "PE"
    moneyness: str       # "OTM" or "ITM"
    expiry: str          # ISO date string


def load_instrument_master(path: str = config.INSTRUMENT_MASTER_PATH) -> List[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def nearest_expiry(rows: List[dict], instrument_master_name: str, min_strikes: int = 10,
                    min_days_out: int = 5) -> str:
    from collections import Counter
    from datetime import date as _date
    counts = Counter(
        r["expiry"] for r in rows
        if r.get("name", "").upper() == instrument_master_name.upper() and r.get("expiry")
    )
    today = _date.today()
    expiries = sorted(
        e for e, c in counts.items()
        if c >= min_strikes and (_date.fromisoformat(e) - today).days >= min_days_out
    )
    if not expiries:
        raise ValueError(f"No expiries with sufficient strikes found for {instrument_master_name}")
    return expiries[0]


def get_spot_instrument_key(commodity_key: str, instrument_rows: List[dict],
                             min_days_out: int = 5) -> str:
    from datetime import date as _date

    cfg = config.COMMODITIES[commodity_key]
    instrument_master_name = cfg["instrument_master_name"]
    ts_prefix = cfg["tradingsymbol_prefix"]
    ts_exclude_prefix = cfg.get("tradingsymbol_exclude_prefix")
    today = _date.today()

    candidates = []
    for r in instrument_rows:
        if r.get("name", "").upper() != instrument_master_name.upper():
            continue
        if r.get("instrument_type") not in ("FUTCOM", "FUTIDX"):
            continue
        tsym = r.get("tradingsymbol", "").upper()
        if not tsym.startswith(ts_prefix.upper()):
            continue
        if ts_exclude_prefix and tsym.startswith(ts_exclude_prefix.upper()) and ts_prefix.upper() != ts_exclude_prefix.upper():
            continue
        expiry = r.get("expiry")
        if not expiry:
            continue
        try:
            days_out = (_date.fromisoformat(expiry) - today).days
        except ValueError:
            continue
        if days_out >= min_days_out:
            candidates.append((expiry, r["instrument_key"], r["tradingsymbol"]))

    if not candidates:
        raise ValueError(f"No valid spot/futures contract found for {commodity_key}")

    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


def build_strikes(commodity_key: str, day_open_spot: float,
                   instrument_rows: List[dict]) -> List[OptionInstrument]:
    cfg = config.COMMODITIES[commodity_key]
    instrument_master_name = cfg["instrument_master_name"]
    ts_prefix = cfg["tradingsymbol_prefix"]
    ts_exclude_prefix = cfg.get("tradingsymbol_exclude_prefix")
    expiry = nearest_expiry(instrument_rows, instrument_master_name)

    calls_above, calls_below = [], []
    puts_below, puts_above = [], []

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

        if opt_type == "CE":
            if strike > day_open_spot:
                calls_above.append((strike, r))
            elif strike < day_open_spot:
                calls_below.append((strike, r))
        elif opt_type == "PE":
            if strike < day_open_spot:
                puts_below.append((strike, r))
            elif strike > day_open_spot:
                puts_above.append((strike, r))

    calls_above.sort(key=lambda x: x[0])
    ce_otm = calls_above[:config.STRIKES_PER_SIDE_OTM]

    calls_below.sort(key=lambda x: x[0], reverse=True)
    ce_itm = calls_below[:config.STRIKES_PER_SIDE_ITM]

    puts_below.sort(key=lambda x: x[0], reverse=True)
    pe_otm = puts_below[:config.STRIKES_PER_SIDE_OTM]

    puts_above.sort(key=lambda x: x[0])
    pe_itm = puts_above[:config.STRIKES_PER_SIDE_ITM]

    result = []
    for strike, r in ce_otm:
        result.append(OptionInstrument(r["instrument_key"], r["tradingsymbol"], strike, "CE", "OTM", expiry))
    for strike, r in ce_itm:
        result.append(OptionInstrument(r["instrument_key"], r["tradingsymbol"], strike, "CE", "ITM", expiry))
    for strike, r in pe_otm:
        result.append(OptionInstrument(r["instrument_key"], r["tradingsymbol"], strike, "PE", "OTM", expiry))
    for strike, r in pe_itm:
        result.append(OptionInstrument(r["instrument_key"], r["tradingsymbol"], strike, "PE", "ITM", expiry))
    return result
