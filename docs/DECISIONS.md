# DECISIONS — lightweight decision log
Format: date · decision · why · alternatives · consequence. Keep each to 3–5 lines. Add as you go.

## D-001 Serve a committed snapshot, not live Elexon calls
Why: deterministic demo, no rate-limit/outage risk for reviewers, fast. Alternative: live fetch with cache (more moving parts). Consequence: ingest script must be re-runnable and documented.

## D-002 Decision cutoff is a configurable assumption (default 09:00 UTC on D-1)
Why: the brief says "one day before delivery" without a time; the market has real cutoffs we choose not to model. Consequence: UI states the assumption; cutoff selector drives all numbers.

## D-003 Error sign: forecast − actual
Why: positive = over-forecast = buyer risk. Consequence: all labels explain it in plain English.

## D-004 Hourly pairing rule (Option C chosen over A and B)
Why: WINDFOR is hourly, FUELHH is 30-min. Option A (H:00 only) ignores half the actual data. Option B (WINDFOR repeated for :30) invents data. Option C (mean of H:00 and H:30) uses all FUELHH data without fabricating forecast points.
Sensitivity result (computed on full January 2026 snapshot at 09:00 cutoff, n=744/744):
- Option C (mean of H:00 & H:30): MAE = 2142.12 MW, RMSE = 2611.70 MW, Bias = +1851.90 MW, nMAE = 18.50%.
- Option A (H:00 only): MAE = 2127.48 MW, RMSE = 2606.07 MW, Bias = +1851.53 MW, nMAE = 18.37%.
- Difference (A - C): MAE diff = -14.64 MW (-0.68% relative), Bias diff = -0.38 MW (-0.02% relative), RMSE diff = -5.63 MW.
Conclusion: The pairing rule choice causes under 0.7% difference in MAE and virtually zero (<0.02%) difference in bias. Option C is robust, fully utilizes both settlement periods, and is disclosed on the Method page. Denominator = 744 (24 h × 31 days).


## D-005 Vintage selection uses real publishTime from WINDFOR
Why: WINDFOR publish clock times are mostly regular (02:30, 04:30, 07:30, 09:30, 11:30, 15:30, 18:30, 22:30 UTC) but one exception observed (12:25 instead of 11:30). Do not hardcode clock times. Use actual `publishTime` values from the snapshot. Consequence: vintage selection is always exact, never approximated from a schedule.

## D-006 Jan-1 coverage confirmed; ingest starts 2025-12-29
Why: Earliest publishTime in snapshot is 2025-12-29T02:30:00Z. For Jan 1 at 09:00 cutoff (D-1 = Dec 31T09:00Z), the latest eligible vintage is 2025-12-31T07:30:00Z — all 24 Jan 1 target hours have coverage. Consequence: ingest window Dec 29–Jan 31 is sufficient; no coverage gap on Jan 1 at the default cutoff.

## D-007 Hosting: Vercel OK (spike measurements and limits)
Why: Vercel documented limits are 250 MB uncompressed (500 MB on modern Python runtime, up to 5 GB with VERCEL_SUPPORT_LARGE_FUNCTIONS) and 50 MB compressed zip. Measured production dependency bundle (FastAPI, Pydantic, Pandas, NumPy, HTTPX, dateutil) is 154 MB uncompressed and 40 MB zipped on Linux (161 MB / 46 MB on macOS). Both fit comfortably within Vercel's limits.
Alternatives: Heroku container (verified working via Dockerfile and compose, zero bundle limit, but slower free/cheap cold starts).
Consequence: Proceed with Vercel monorepo deployment via vercel.json and api/index.py; Heroku container kept ready as fallback.

## D-008 Reporting of forecast bias (do not bias-correct raw data)
Date: 2026-10-27
Decision: Do NOT apply artificial bias correction or calibrate raw forecasts. Report the raw empirical bias (+1,852 MW / +16%) transparently alongside random error ($MSE = \text{Bias}^2 + \text{Variance}$ breakdown). The risk band continues using empirical error quantiles (which naturally shift for bias) and explicitly reports `bias_used_mw` so buyers see "cushion = X MW of which Y MW is systematic bias".
Why: Diagnostics proved the bias is real, stable across 27/31 days, and present at all hours/horizons, while the forecast retains strong meteorological skill ($r=0.926$, beating persistence by 50%). A plausible industry cause is fleet scope mismatch (National Grid ESO WINDFOR total wind vs BMRS FUELHH transmission-metered wind) or curtailment, but BMRS data alone cannot confirm this. Altering raw numbers would obscure operational reality.
Alternatives: Multiplicative scaling (0.8x) or offset subtraction. Rejected: hides true market outturn and introduces untraceable assumptions.
Consequence: New fields in `/api/accuracy/summary` and `/api/risk/band`; UI displays the bias-variance decomposition and explanatory note on Method page.

