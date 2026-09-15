"""
MCX Scanner-3 — Main Orchestrator (v4, rolling-reference spike detection)
=============================================================================
Run flow (once per commodity: Crude Oil, Natural Gas, Gold, Silver):

  1. Load instrument master, resolve spot instrument key dynamically
  2. Get spot day-open + current price (for spot trend context only)
  3. Build strikes: 15 CE (10 OTM + 5 ITM) + 15 PE (10 OTM + 5 ITM)
  4. For each strike: compare CURRENT premium against the price saved
     from the LAST run (rolling reference, via price_history.py) —
     NOT the day's fixed opening premium. This catches a spike as it
     happens instead of lagging behind a big cumulative move from
     market open that may already be reversing.
     -> if move >= threshold: send a Premium Spike Alert
  5. Save this run's prices as the reference for the NEXT run
  6. Separately: check spot volume spike vs 18-day average, alert if so
"""

from datetime import date, timedelta

import config
import strike_builder
import data_fetcher
import volume_alert
import telegram_notify
import price_history


def _date_range(days_back: int):
    today = date.today()
    return (today - timedelta(days=days_back)).isoformat(), today.isoformat()


def run_commodity(commodity_key: str, spot_instrument_key: str, instrument_rows, history: dict):
    cfg = config.COMMODITIES[commodity_key]
    min_move = cfg["min_move_rupees"]

    # Spot day-open + current — kept only for the "Spot Trend" context line
    day_open_spot = data_fetcher.get_day_open_price(spot_instrument_key)
    current_spot = data_fetcher.get_live_ltp(spot_instrument_key)

    strikes = strike_builder.build_strikes(commodity_key, day_open_spot, instrument_rows)

    for inst in strikes:
        try:
            current_premium = data_fetcher.get_live_ltp(inst.instrument_key)
        except Exception as e:
            print(f"[{commodity_key}] skipping {inst.trading_symbol} (no data: {e})")
            continue

        ref = price_history.get_reference(history, inst.instrument_key)

        # Always update the reference for next run, regardless of whether
        # this run alerts — the rolling window keeps moving forward.
        price_history.update_reference(history, inst.instrument_key, current_premium)

        if ref is None:
            # No usable recent reference (first run of the day, or a gap
            # after a missed run) — just seed it, nothing to compare yet.
            continue

        reference_premium, age_minutes = ref
        move = abs(current_premium - reference_premium)

        if move < min_move:
            continue

        message = telegram_notify.format_strike_alert(
            commodity_key=commodity_key,
            symbol=inst.trading_symbol,
            option_type=inst.option_type,
            moneyness=inst.moneyness,
            strike=inst.strike,
            reference_premium=reference_premium,
            reference_age_minutes=age_minutes,
            current_premium=current_premium,
            move=move,
            day_open_spot=day_open_spot,
            current_spot=current_spot,
        )
        telegram_notify.send_telegram_message(message)

    from_d, to_d = _date_range(config.VOLUME_AVG_LOOKBACK_DAYS + 5)
    spot_daily = data_fetcher.get_historical_ohlc(spot_instrument_key, "day", from_d, to_d)
    spike = volume_alert.check_volume_spike(spot_daily)
    if spike:
        telegram_notify.send_telegram_message(
            telegram_notify.format_volume_alert(commodity_key, spike)
        )


def main():
    instrument_rows = strike_builder.load_instrument_master()
    history = price_history.load_history()

    for commodity_key in config.COMMODITIES:
        try:
            spot_instrument_key = strike_builder.get_spot_instrument_key(commodity_key, instrument_rows)
            run_commodity(commodity_key, spot_instrument_key, instrument_rows, history)
        except Exception as e:
            print(f"[{commodity_key}] scan failed: {e}")

    price_history.save_history(history)


if __name__ == "__main__":
    main()
