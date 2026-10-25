# DOMAIN — what the engineer must understand first

## Day-ahead market in one paragraph
GB power is traded in a day-ahead auction. Buyers submit volumes for each half-hour of the *next* day before a morning cutoff on day D-1. They must therefore estimate how much of the next day's demand will be met by wind and how much they must buy elsewhere. If wind under-delivers versus forecast, they are short and face balancing/imbalance cost; if it over-delivers they are long. So the cost of error is asymmetric and the *size and direction* of past forecast errors is decision information. (The exact auction cutoff times are a market detail we do not model; we use a configurable cutoff, see SPEC A2.)

## Settlement periods and time
- A settlement period is 30 minutes; 48 per day (46/50 on clock-change days, not in January).
- January is GMT, so UTC = UK local time. Still store and compute in UTC; convert only for labels.
- `startTime` = beginning of the half-hour the value refers to (the **target**).

## Vintages (the core idea)
A forecast for the same target `startTime` is **re-published many times** with different `publishTime`. Each published version is a *vintage*. Key derived quantities:
- `horizon_h = (startTime − publishTime)` in hours: how far ahead the forecast was made.
- **Forecast at decision time** for target t = the vintage with the greatest `publishTime` that is ≤ cutoff(t). Anything published after the cutoff is *unknown to the buyer* and must not be used (no look-ahead).
- Evaluating accuracy only on the latest-ever forecast would flatter the forecast. That is the main analytical trap here.

## Datasets (verify every field against a real response before coding)
Base URL (open, no key): `https://data.elexon.co.uk/bmrs/api/v1`. OpenAPI spec is published by Elexon (look for the swagger JSON under `https://data.elexon.co.uk`). Documentation pages given in the brief:
- `datasets/FUELHH/stream` — half-hourly generation by fuel type. Use `fuelType = WIND`. Fields of interest: `startTime`, `generation` (MW); also expect `settlementDate`, `settlementPeriod`, `fuelType`, `dataset`. **`publishTime` on FUELHH rows is unverified** — it may or may not exist. The loader and tests must not assume it. Deduplication rule (A6): if `publishTime` is present, keep the row with the latest `publishTime` per `(startTime, fuelType)` key; if absent, drop exact duplicate rows only. Record what is actually observed in T1.1 and update this line.
- `datasets/WINDFOR/stream` — wind generation forecast. Fields: `startTime`, `publishTime`, `generation` (MW). `publishTime` is expected and required for vintage selection.
**To verify (do not assume):** accepted query parameters and which are required (likely `publishDateTimeFrom/To` and/or `settlementDateFrom/To`, optional `fuelType` filter); maximum date range per request; whether the stream returns a bare JSON array or `{data: []}`; forecast horizon range and publish frequency in WINDFOR; whether FUELHH has multiple publications per period; whether WINDFOR data exists back to 2025-12-29 (needed for Jan 1 D-1 forecasts — if absent, Jan 1 coverage may be zero at the default cutoff); rate limits. Ingest in chunks (e.g. 1–3 days per request) with retries and polite delays.

## Known data caveats to surface, not hide
- FUELHH "WIND" and WINDFOR may not cover exactly the same fleet (e.g. embedded wind). A persistent bias in the errors may reflect that, so report bias plainly and mention this in the Method page as a *possible* cause, labelled as hypothesis.
- Some targets may have no vintage before the cutoff (coverage < 100%).
- Zero or very low actuals make percentage errors unstable, so use normalised MAE (divide by mean actual over the window) instead of MAPE.

## Metric definitions (n = number of target periods with both forecast-at-cutoff and actual)
- error_i = forecast_i − actual_i
- MAE = mean(|error_i|)
- RMSE = sqrt(mean(error_i²))
- Bias (mean error) = mean(error_i)  (positive = systematic over-forecast)
- nMAE = MAE / mean(actual_i)  (report as %)
- Pxx absolute error = xx-th percentile of |error_i| (linear interpolation; document it)
- Over-forecast tail: P90 of max(error_i, 0) over all periods, and worst single over-forecast
- Coverage = n / (number of target periods in range)
- By-horizon view: evaluate **every vintage in the snapshot** regardless of cutoff (the `/api/accuracy/by-horizon` endpoint takes no `cutoff_hour` parameter). Bucket by horizon_h (e.g. 0–6, 6–12, 12–24, 24–36, 36–48, 48+), compute the same metrics per bucket. Shows how accuracy decays with lead time and why the decision-time horizon matters. Contrast with the summary, by-hour, daily and distribution endpoints, which use only the forecast-at-cutoff vintage for each target.
- Risk band for day D (FR-7): for each hour-of-day (or all periods pooled if sparse), take empirical quantiles of error from delivery days strictly before D at the same cutoff; band = forecast − q_hi … forecast − q_lo, clipped at ≥ 0 MW. State that this is empirical, not a guarantee.

## Glossary for the UI copy
Forecast at decision time · Forecast age (hours between publish and cutoff) · Lead time (horizon) · Over-forecast (forecast above what happened) · Under-forecast · Bias · Cushion (MW).
