# MCX Scanner (Scanner-3 — MCX Variant)

## என்ன பண்ணுது
Crude Oil, Natural Gas, Gold, Silver — நான்கு MCX commodities-க்கும்:

1. அன்றைக்கு market-open spot price base-ஆ 10 OTM CE + 10 OTM PE strikes தேர்ந்தெடுக்கும் (nearest monthly expiry)
2. ஒவ்வொரு strike-ஓட premium-ம் day-open price-ல இருந்து எவ்வளவு move ஆச்சுன்னு பாக்கும்:
   - Crude Oil ₹10, Natural Gas ₹3, Gold ₹20, Silver ₹15 — இதை தாண்டினா மட்டும் alert
3. Move ஆன strikes-க்கு Daily CPR (Pivot Boss classification) காட்டும்
4. ஒவ்வொரு commodity-ஓட Spot-க்கும் Weekly CPR + Daily CPR காட்டும்
5. Spot-ஓட Volume-ஐ 18-day average உடன் compare பண்ணி, spike ஆனா buying/selling direction-உடன் தனி அலர்ட்
6. எல்லாத்தையும் ஒரு Telegram message-ஆ அனுப்பும் (commodity-க்கு ஒண்ணு)

## Files
| File | வேலை |
|---|---|
| `config.py` | commodities, thresholds, strike count, CPR settings — எல்லாம் இங்க edit பண்ணலாம் |
| `strike_builder.py` | instrument master CSV-ல இருந்து 10 CE + 10 PE தேர்வு |
| `cpr_calculator.py` | Narrow/Wide/Virgin + Higher/Lower/Overlapping/Inside/Outside Value CPR classification |
| `data_fetcher.py` | Upstox API calls — OHLC history, day-open, live LTP |
| `volume_alert.py` | 18-day average volume vs today spike check |
| `telegram_notify.py` | Telegram message formatting + sending |
| `mcx_scanner_main.py` | எல்லாத்தையும் இணைக்கும் orchestrator — இதுதான் entry point |
| `mcx_scanner_workflow.yml` | GitHub Actions schedule (`.github/workflows/` folder-க்குள் copy பண்ணுங்க) |

## நீங்க பண்ண வேண்டியது (Setup)

1. **`manual_login.py`** — உங்க Scanner-4-ல already இருக்கிற Upstox manual login script-ஐ இந்த repo-க்கும் copy பண்ணுங்க (இது access token generate பண்ணும்).

2. **Instrument keys** — `mcx_scanner_main.py`-ல `SPOT_INSTRUMENT_KEYS` dict-ல ஒவ்வொரு commodity-ஓட spot/futures instrument_key-ஐ Upstox instrument master-ல இருந்து எடுத்து போடுங்க.

3. **Strike intervals** — `config.py`-ல `strike_step` values approximate-ஆ போட்டிருக்கேன் (Crude ₹50, Natural Gas ₹5, Gold ₹50, Silver ₹100). Real instrument master CSV-ல இருந்து actual intervals verify பண்ணுங்க — code-ல அது direct-ஆ CSV-ல இருந்து strikes படிக்குதுனாலே இந்த value cosmetic தான், correctness-க்கு affect பண்ணாது.

4. **GitHub Secrets** வேணும்:
   - `UPSTOX_API_KEY`, `UPSTOX_API_SECRET`, `UPSTOX_TOTP_SECRET`
   - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

5. **Cron timing** — `mcx_scanner_workflow.yml`-ல schedule adjust பண்ணிக்கலாம் (இப்போ 15 நிமிடத்துக்கு ஒரு தடவை வெச்சிருக்கேன்).

## கவனிக்க வேண்டியது
- Narrow/Wide CPR threshold (`NARROW_CPR_THRESHOLD_PCT`, `WIDE_CPR_THRESHOLD_PCT`) approximate values — உங்க actual trading data வெச்சு backtest பண்ணி fine-tune பண்ணிக்கலாம்.
- Volume spike multiplier (1.5x) தற்போதைக்கு default — இதுவும் adjust பண்ணலாம்.
- இது MCX options premium-ல CPR calculate பண்றது (underlying-ல இல்ல) — உங்க spec படியே.
- 
