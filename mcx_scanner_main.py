"""
MCX Scanner-3 — Main Orchestrator (v2, simplified)
=====================================================
Run flow (once per commodity: Crude Oil, Natural Gas, Gold, Silver):

  1. Load instrument master, find nearest monthly expiry
  2. Get spot day-open price -> build strikes:
       15 CE (10 OTM + 5 ITM) + 15 PE (10 OTM + 5 ITM) = 30 strikes
  3. For each strike: get day-open premium + current premium
       -> if move >= commodity's min_move_rupees: send a Premium Spike Alert
          (includes spot trend: UP/DOWN vs day-open, no CPR)
  4. Separately: check spot volume spike vs 18-day average, alert if so

Intended to run on a schedule via GitHub Actions (e.g. every 5-15 min
during market hours) — see mcx_scanner_workflow.yml
"""

from datetime import date, timedelta

import config
import strike_builder
import data_fetcher
import volume_alert
import telegram_notify


def _date_range(days_back: int):
    today = date.today()
    return (today - timedelta(days=days_back)).isoformat(), today.isoformat()


def run_commodity(commodity_key: str, spot_instrument_key: str, instrument_rows):
    cfg = config.COMMODITIES[commodity_key]
    min_move = cfg["min_move_rupees"]

    # --- 1. Spot day-open price + current price (for spot trend) ---
    day_open_spot = data_fetcher.get_day_open_price(spot_instrument_key)
    current_spot = data_fetcher.get_live_ltp(spot_instrument_key)

    # --- 2. Build strikes around day-open spot (15 CE + 15 PE) ---
    strikes = strike_builder.build_strikes(commodity_key, day_open_spot, instrument_rows)

    # --- 3. Per-strike premium move check -> send alert immediately if it qualifies ---
    for inst in strikes:
        day_open_premium = data_fetcher.get_day_open_price(inst.instrument_key)
        current_premium = data_fetcher.get_live_ltp(inst.instrument_key)
        move = abs(current_premium - day_open_premium)

        if move < min_move:
            continue

        message = telegram_notify.format_strike_alert(
            commodity_key=commodity_key,
            symbol=inst.trading_symbol,
            option_type=inst.option_type,
            moneyness=inst.moneyness,
            strike=inst.strike,
            day_open_premium=day_open_premium,
            current_premium=current_premium,
            move=move,
            day_open_spot=day_open_spot,
            current_spot=current_spot,
        )
        telegram_notify.send_telegram_message(message)

    # --- 4. Volume spike check (index/spot level) ---
    from_d, to_d = _date_range(config.VOLUME_AVG_LOOKBACK_DAYS + 5)
    spot_daily = data_fetcher.get_historical_ohlc(spot_instrument_key, "day", from_d, to_d)
    spike = volume_alert.check_volume_spike(spot_daily)
    if spike:
        telegram_notify.send_telegram_message(
            telegram_notify.format_volume_alert(commodity_key, spike)
        )


# Map each commodity to its MCX spot/futures instrument_key.
# Confirmed against MCX instrument master (uploaded 2026-08-25):
#   - Near-month standard-lot contract for Crude Oil, Natural Gas, Silver
#   - Gold Mini (GOLDM) for Gold, per Logesh's confirmation
# NOTE: these are near-month contracts and WILL need periodic updating as
# they approach expiry (Gold Mini/Silver ~2026-09-04, Natural Gas 2026-09-25,
# Crude Oil 2026-09-21). Re-check the instrument master each time you roll forward.
SPOT_INSTRUMENT_KEYS = {
    "CRUDEOIL": "MCX_FO|565899",     # CRUDEOIL26SEPFUT
    "NATURALGAS": "MCX_FO|568245",   # NATURALGAS26SEPFUT
    "GOLD": "MCX_FO|563946",         # GOLDM26SEPFUT (Mini)
    "SILVER": "MCX_FO|471725",       # SILVER26SEPFUT
}


def main():
    instrument_rows = strike_builder.load_instrument_master()
    for commodity_key in config.COMMODITIES:
        try:
            run_commodity(commodity_key, SPOT_INSTRUMENT_KEYS[commodity_key], instrument_rows)
        except Exception as e:
            print(f"[{commodity_key}] scan failed: {e}")


if __name__ == "__main__":
    main()
  
