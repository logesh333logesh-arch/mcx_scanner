"""
MCX Scanner-3 — Main Orchestrator
====================================
Run flow (once per commodity: Crude Oil, Natural Gas, Gold, Silver):

  1. Load instrument master, find nearest monthly expiry
  2. Get spot day-open price -> build 10 OTM CE + 10 OTM PE strikes
  3. For each strike: get day-open premium + current premium
       -> if move >= commodity's min_move_rupees: candidate for alert
  4. For candidate strikes: compute Daily CPR (Pivot Boss classification)
       on the option premium OHLC series
  5. Compute spot Weekly CPR + spot Daily CPR (once per commodity, not
     per strike) and attach to every alert for that commodity
  6. Separately: check spot volume spike vs 18-day average
  7. Send one combined Telegram message per commodity with all of the
     above (skips sending anything if no strikes qualify and no
     volume spike detected)

Intended to run on a schedule via GitHub Actions (e.g. every 5-15 min
during market hours) — see .github/workflows/mcx_scanner.yml
"""

from datetime import date, timedelta

import config
import strike_builder
import data_fetcher
import cpr_calculator
import volume_alert
import telegram_notify


def _date_range(days_back: int):
    today = date.today()
    return (today - timedelta(days=days_back)).isoformat(), today.isoformat()


def run_commodity(commodity_key: str, spot_instrument_key: str, instrument_rows):
    cfg = config.COMMODITIES[commodity_key]
    min_move = cfg["min_move_rupees"]

    # --- 1. Spot day-open price ---
    day_open_spot = data_fetcher.get_day_open_price(spot_instrument_key)

    # --- 2. Build strikes around day-open spot ---
    strikes = strike_builder.build_strikes(commodity_key, day_open_spot, instrument_rows)

    # --- 3. Spot CPR (daily + weekly), shared across this commodity's alerts ---
    from_d, to_d = _date_range(config.NARROW_CPR_LOOKBACK_DAYS + 5)
    spot_daily = data_fetcher.get_historical_ohlc(spot_instrument_key, "day", from_d, to_d)
    spot_weekly = data_fetcher.get_historical_ohlc(spot_instrument_key, "week", from_d, to_d)

    spot_daily_cls = cpr_calculator.full_classification(spot_daily)
    spot_weekly_cls = cpr_calculator.full_classification(spot_weekly)

    spot_daily_label = f"{spot_daily_cls['width_type']} / {spot_daily_cls['relationship_type']}"
    spot_weekly_label = f"{spot_weekly_cls['width_type']} / {spot_weekly_cls['relationship_type']}"

    messages = []

    # --- 4. Per-strike premium move + CPR check ---
    for inst in strikes:
        day_open_premium = data_fetcher.get_day_open_price(inst.instrument_key)
        current_premium = data_fetcher.get_live_ltp(inst.instrument_key)
        move = abs(current_premium - day_open_premium)

        if move < min_move:
            continue

        opt_from_d, opt_to_d = _date_range(config.NARROW_CPR_LOOKBACK_DAYS + 5)
        opt_daily = data_fetcher.get_historical_ohlc(inst.instrument_key, "day", opt_from_d, opt_to_d)
        opt_cls = cpr_calculator.full_classification(opt_daily)
        strike_cpr_label = f"{opt_cls['width_type']} / {opt_cls['relationship_type']}"

        messages.append(telegram_notify.format_strike_alert(
            commodity=commodity_key,
            symbol=inst.trading_symbol,
            option_type=inst.option_type,
            strike=inst.strike,
            day_open_premium=day_open_premium,
            current_premium=current_premium,
            move=move,
            strike_daily_cpr=strike_cpr_label,
        ))

    # --- 5. Volume spike check ---
    spike = volume_alert.check_volume_spike(spot_daily)

    if not messages and not spike:
        return  # nothing to report for this commodity right now

    full_message = telegram_notify.format_spot_cpr_block(
        commodity_key, spot_weekly_label, spot_daily_label
    )
    if spike:
        full_message += "\n" + telegram_notify.format_volume_alert(commodity_key, spike)
    if messages:
        full_message += "\n" + "\n".join(messages)

    telegram_notify.send_telegram_message(full_message)


# Map each commodity to its MCX futures instrument_key (used as spot/underlying
# proxy for CPR + volume calculations). Filled in from Logesh's Aug 2026
# MCX instrument master — update these when contracts roll to next month.
SPOT_INSTRUMENT_KEYS = {
    "CRUDEOIL": "MCX_FO|565899",     # CRUDEOIL26SEPFUT, expiry 2026-09-21, lot 100
    "NATURALGAS": "MCX_FO|568245",   # NATURALGAS26SEPFUT, expiry 2026-09-25, lot 1250
    "GOLD": "MCX_FO|563946",         # GOLDM26SEPFUT (Mini), expiry 2026-09-04, lot 100
    "SILVER": "MCX_FO|471725",       # SILVER26SEPFUT, expiry 2026-09-04, lot 30
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
  
