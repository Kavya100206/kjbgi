# DOMAIN — what the engineer must understand first

## Day-ahead market in one paragraph
GB power is traded in a day-ahead auction. Buyers submit volumes for each half-hour of the *next* day before a morning cutoff on day D-1. They must therefore estimate how much of the next day's demand will be met by wind and how much they must buy elsewhere. If wind under-delivers versus forecast, they are short and face balancing/imbalance cost; if it over-delivers they are long. So the cost of error is asymmetric and the *size and direction* of past forecast errors is decision information. (The exact auction cutoff times are a market detail we do not model; we use a configurable cutoff, see SPEC A2.)

## Settlement periods and time
- A settlement period is 30 minutes; 48 per day (46/50 on clock-change days, not in January).
- January is GMT, so UTC = UK local time. Still store and compute in UTC; convert only for labels.
- `startTime` = beginning of the half-hour (FUELHH) or hour (WINDFOR) the value refers to (the **target**).

## Vintages (the core idea)
A forecast for the same target `startTime` is **re-published multiple times** with different `publishTime`. Each published version is a *vintage*. Key derived quantities:
- `horizon_h = (startTime − publishTime)` in hours: how far ahead the forecast was made.
- **Forecast at decision time** for target t = the vintage with the greatest `publishTime` that is ≤ cutoff(t). Anything published after the cutoff is *unknown to the buyer* and must not be used (no look-ahead).
- Evaluating accuracy only on the latest-ever forecast would flatter the forecast. That is the main analytical trap here.

## Datasets — CONFIRMED fields from T1.1 (2026-10-26)
Base URL (open, no key): `https://data.elexon.co.uk/bmrs/api/v1`.

### FUELHH/stream
**Confirmed fields (7):** `dataset`, `publishTime`, `startTime`, `settlementDate`, `settlementPeriod`, `fuelType`, `generation`
- `publishTime`: UTC ISO 8601 (`YYYY-MM-DDTHH:MM:SSZ`). Present and confirmed. Observed pattern: `publishTime = startTime + 30 min` (published at the end of each settlement period).
- `startTime`: UTC, **30-minute resolution** (`:00:00` and `:30:00`).
- `generation`: integer, MW.
- No duplicate `startTime` rows observed for WIND in the full January window (1,536 rows, 0 duplicates). Deduplication rule (A6): drop exact duplicates.
- **Query params to use:** `settlementDateFrom` / `settlementDateTo` (format `YYYY-MM-DD`); `fuelType=WIND`. The `/stream` endpoint returns a **bare JSON array**.
- Do NOT use `publishDateTimeFrom/To` for actuals unless specifically needed (it shifts the date range relative to publish time, not settlement date).
- Tested 32-day window (Jan 1–Feb 1) in one request: 1,536 rows, HTTP 200, ~0.7 s.

### WINDFOR/stream
**Confirmed fields (4):** `dataset`, `publishTime`, `startTime`, `generation`
- No `settlementDate`, `settlementPeriod`, or `fuelType` field. WINDFOR is wind-only.
- `publishTime`: UTC ISO 8601. Required for vintage selection.
- `startTime`: UTC, **HOURLY resolution** (`:00:00` only — not 30-minute). **This differs from FUELHH.** See A7 pairing rule in SPEC.
- `generation`: integer, MW. We cannot confirm from source data whether this is an hour-average or an instantaneous value at the boundary hour. This uncertainty is documented in SPEC A7 and the Method page.
- **Publish cadence:** 8 times per day. Observed clock times: **02:30, 04:30, 07:30, 09:30, 11:30, 15:30, 18:30, 22:30 UTC**. One exception observed in the January window: one day had 12:25 instead of 11:30. **Do not hardcode these clock times** in ingest or tests — use the observed `publishTime` values from the API.
- **Horizon range observed:** forward forecasts range from **0.5 h to 66.5 h**. In addition, **20.6% of WINDFOR rows (4,081 records) are retrospective backcasts (`horizon < 0`)** spanning up to −25.5 h before publish time. Decision-time vintage selection automatically excludes retrospective records because for any target hour t on delivery day D, `cutoff(t) = D-1 @ cutoff_hour < t`, so `publishTime <= cutoff < t` guarantees `horizon_h = startTime − publishTime > 0`. The `/api/accuracy/by-horizon` endpoint must explicitly filter out `horizon < 0` and report the count of excluded retrospective records.
- **Horizon buckets to use:** `<12, 12–24, 24–36, 36–48, 48–60, 60–67` hours.
- **Query params to use:** `publishDateTimeFrom` / `publishDateTimeTo` (ISO 8601 UTC). **Do NOT use `settlementDateFrom/To` for historical WINDFOR** — that parameter returns the current live forecast, not historical data.
- The `/stream` endpoint returns a **bare JSON array**. The non-stream `/datasets/WINDFOR` endpoint returns `{"data": [...]}`.
- **Historical depth confirmed:** data exists back to at least 2025-12-29T02:30:00Z. Jan 1 targets have a vintage published 2025-12-31T07:30:00Z, which is before the 09:00 cutoff. Jan 1 at 09:00 cutoff = **full coverage** (24 hours).
- **Ingest strategy:** 7-day chunks on `publishDateTimeFrom/To`; 0.5 s delay between requests; retry on error.
- Tested 34-day window (Dec 29–Jan 31) in one request: 19,856 rows, HTTP 200, ~64 s. No rate-limit errors. Will chunk anyway for robustness.

### Snapshot size estimate
| Dataset | Rows | Raw JSON | Gzipped |
|---|---|---|---|
| FUELHH (Jan 1–Feb 1) | 1,536 | 272 KB | ~15 KB |
| WINDFOR (Dec 29–Jan 31) | 19,856 | 2.2 MB | ~102 KB |
| **Total** | **21,392** | **~2.5 MB** | **~114 KB** |

Store as `actuals.csv.gz` and `forecasts.csv.gz` — plain CSV.gz is adequate and keeps the repo tiny.

## Known data caveats to surface, not hide
- **Systematic January 2026 Over-Forecast Bias:** Phase 2.5 diagnostics confirmed that the WINDFOR forecast at the 09:00 decision cutoff exhibits a persistent positive bias of **+1,851.90 MW** (~16.0% above mean actual of 11,580.74 MW). Bias accounts for ~86% of MAE (2,142.12 MW) and ~50% of MSE ($\text{Bias}^2/\text{MSE} = 50.3\%$). It is present across 27 of 31 days (87.1%), in all 24 hours of the day (ranging from +1,365 to +2,463 MW), and across all lead horizons from <12h to 60h.
- **Fleet Scope & Curtailment Hypothesis (Unverified):** A plausible industry cause is a fleet scope mismatch: National Grid ESO WINDFOR models total Great Britain wind generation (including distribution-connected embedded wind farms), whereas BMRS FUELHH reports metered generation from Transmission-System BMUs only. Another contributing factor may be commercial wind curtailment through the Balancing Mechanism. However, because Elexon BMRS does not supply embedded wind metering or bid-offer curtailment acceptance flags in these feeds, **any physical fleet or curtailment attribution is an unverified hypothesis**. The data must NOT be artificially bias-corrected; instead, report empirical bias and error standard deviation transparently.
- **Meteorological Skill Despite Bias:** Despite the systematic offset, the forecast demonstrates strong meteorological skill, with a Pearson correlation of $r = 0.9255$ against actuals and a 50.0% MAE improvement over a 24-hour persistence baseline ($r = 0.2130$).
- Some targets may have no vintage before the cutoff (coverage < 100%).
- If either half-hour of FUELHH is missing for a target hour, that hour is excluded from metrics (A7).
- Zero or very low actuals make percentage errors unstable, so use normalised MAE (divide by mean actual over the window) instead of MAPE.
- We cannot confirm whether WINDFOR `generation` is an hour-average or instantaneous value. The sensitivity check (Option A vs Option C pairing) is documented in DECISIONS.md D-004.
- **By-hour lead-time confounding:** at the 09:00 UTC cutoff, the decision-time forecast lead time for delivery day D's hours ranges from **~16.5 h** (for 00:00Z delivery) to **~39.5 h** (for 23:00Z delivery). Because hour-of-day is naturally confounded with lead time (later delivery hours always have longer lead times from a fixed morning cutoff), the by-hour error view reflects both diurnal wind patterns and forecast decay. The UI must state this confounding note directly next to the by-hour chart.

## Metric definitions (n = number of target hours with both forecast-at-cutoff and paired actual)
- error_i = forecast_i − actual_i (actual_i = hourly mean per A7)
- MAE = mean(|error_i|)
- RMSE = sqrt(mean(error_i²))
- Bias (mean error) = mean(error_i)  (positive = systematic over-forecast)
- nMAE = MAE / mean(actual_i)  (report as %)
- Pxx absolute error = xx-th percentile of |error_i| (linear interpolation; document it)
- Over-forecast tail: P90 of max(error_i, 0) over all periods, and worst single over-forecast
- Coverage = n / (number of target hours in range); for full January = n / 744
- By-horizon view: evaluate **every vintage in the snapshot** regardless of cutoff (the `/api/accuracy/by-horizon` endpoint takes no `cutoff_hour` parameter). Exclude retrospective backcasts (`horizon < 0`) and report the excluded count. Bucket forward forecasts by horizon_h using `<12, 12–24, 24–36, 36–48, 48–60, 60–67`. Shows how accuracy decays with lead time. Contrast with the summary, by-hour, daily and distribution endpoints, which use only the forecast-at-cutoff vintage for each target.
- Risk band for day D (FR-7): for each hour-of-day (or all periods pooled if sparse), take empirical quantiles of error from delivery days strictly before D at the same cutoff; band = forecast − q_hi … forecast − q_lo, clipped at ≥ 0 MW. State that this is empirical, not a guarantee.

## Glossary for the UI copy
Forecast at decision time · Forecast age (hours between publish and cutoff) · Lead time (horizon) · Over-forecast (forecast above what happened) · Under-forecast · Bias · Cushion (MW) · Hourly mean actual (mean of two 30-min FUELHH periods per A7).
