# DATA_REPORT — January 2026 Elexon Snapshot Quality Audit

Audit performed on committed snapshot (`actuals.csv.gz`, `forecasts.csv.gz`, `meta.json`).
Ingest window: FUELHH actuals `2026-01-01` to `2026-02-01`; WINDFOR forecasts published `2025-12-29T00:00:00Z` to `2026-01-31T23:59:59Z`.

---

## 1. Executive Summary

| Metric | Target / Expected | Observed in Snapshot | Status |
|---|---|---|---|
| **Vintages per day** | 8 per day | **8.0** (min 8, median 8, max 8 across all 34 days) | ✅ Perfect |
| **Total unique vintages** | 272 (34 days × 8) | **272** unique `publishTime` timestamps | ✅ Verified |
| **WINDFOR horizon range** | ~3 h to ~72 h | **-25.5 h to +66.5 h** (median 21.5 h); forward forecasts **+0.5 h to +66.5 h** (median 28.6 h) | ✅ Verified |
| **FUELHH actuals gaps (Jan 1–31)** | 0 missing half-hours | **0** missing `H:00`; **0** missing `H:30` (all 1,488 half-hours present) | ✅ 100% complete |
| **Jan 1 coverage (at 09:00 D-1 cutoff)** | 24 / 24 hours | **24 / 24 hours (100.0%)** (vintage `2025-12-31T07:30:00Z`) | ✅ Complete |
| **Full January coverage (at 09:00 D-1 cutoff)** | 744 target hours | **744 / 744 hours (100.00%)** | ✅ Complete |
| **Snapshot compressed size** | ~140 KB | **113.8 KB** (actuals: 14.8 KB, forecasts: 101.7 KB) | ✅ Within budget |

---

## 2. Ingest & Row Counts

- **FUELHH (Wind Actuals):**
  - Raw records retrieved: 1,536 (32 days × 48 settlement periods/day)
  - Duplicate rows dropped: 0 (confirmed unique per `(startTime, fuelType)`)
  - Target window range: `2026-01-01T00:00:00Z` to `2026-02-01T23:30:00Z`
  - Generation range: min 202 MW, median 8,340 MW, max 16,921 MW
- **WINDFOR (Wind Forecasts):**
  - Raw records retrieved: 19,856
  - Duplicate rows dropped: 0 (confirmed unique per `(publishTime, startTime)`)
  - Unique publish times: 272 vintages across 34 days
  - Forecast target window range: `2025-12-28T21:00:00Z` to `2026-02-02T21:00:00Z`
  - Generation range: min 428 MW, median 7,812 MW, max 17,294 MW

---

## 3. WINDFOR Publish Cadence & Horizon Analysis

### 3.1 Vintages per Day
Every single day in the 34-day span (2025-12-29 through 2026-01-31) has exactly 8 published vintages.
Observed publish clock times (UTC):
- Regular cadence: `02:30`, `04:30`, `07:30`, `09:30`, `11:30`, `15:30`, `18:30`, `22:30`.
- Single clock-time anomaly: on 2026-01-15, one vintage was published at `12:25:00Z` instead of `11:30:00Z` (confirmed in T1.1; handled cleanly because vintage selection uses actual `publishTime` timestamps rather than assumed clock schedules).

### 3.2 Forecast Horizon (`startTime - publishTime`)
- **Total records:** 19,856
- **Retrospective / backcast records (horizon < 0):** 4,081 records (20.6%). Elexon includes the preceding ~24 hours of generation estimates in each publish.
- **Forward forecast records (horizon ≥ 0):** 15,775 records (79.4%).
  - Minimum forward lead time: **0.5 h** (30 minutes ahead)
  - 25th percentile: **14.5 h**
  - Median forward lead time: **28.6 h** (~1.2 days ahead)
  - 75th percentile: **42.5 h**
  - Maximum lead time: **66.5 h** (~2.8 days ahead)

Horizon buckets for `/api/accuracy/by-horizon`:
- `<12 h`: 2,448 forward forecast points
- `12–24 h`: 2,720 forward forecast points
- `24–36 h`: 2,720 forward forecast points
- `36–48 h`: 2,720 forward forecast points
- `48–60 h`: 2,720 forward forecast points
- `60+ h`: 2,447 forward forecast points

---

## 4. Actuals Integrity & Missing Half-Hours (A7 Pairing)

The pairing rule (Assumption A7) requires both half-hours (`H:00` and `H:30`) to compute `actual_hourly(H) = mean(FUELHH[H:00], FUELHH[H:30])`. If either half-hour is missing, the entire hour is excluded.

- **January delivery hours:** 31 days × 24 hours = 744 hours.
- **Expected half-hour periods:** 744 × 2 = 1,488 settlement periods.
- **Actuals present in January:** exactly 1,488 periods.
- **Missing `H:00` periods:** 0
- **Missing `H:30` periods:** 0
- **Excluded hours due to missing half-hours:** **0**. All 744 hours in January have both half-hours present.

---

## 5. Decision-Time Coverage (Default 09:00 UTC Cutoff on D-1)

Under Assumption A2, the day-ahead decision for delivery day D is made at 09:00 UTC on day D-1.
The forecast at decision time is the latest vintage with `publishTime <= D-1 09:00:00Z`.

### 5.1 January 1 Delivery Day
- Decision cutoff: `2025-12-31T09:00:00Z`.
- Eligible vintages on Dec 31: `02:30:00Z`, `04:30:00Z`, `07:30:00Z`.
- Selected latest vintage: **`2025-12-31T07:30:00Z`** (forecast age = 1.5 h before decision).
- Jan 1 delivery hours: 24 hours (`2026-01-01T00:00Z` to `2026-01-01T23:00Z`).
- Forecast points available: **24 of 24 (100.0%)**.
- Lead time range for Jan 1: 16.5 h (for 00:00Z delivery) to 39.5 h (for 23:00Z delivery).

### 5.2 Full Month Coverage Table (09:00 Cutoff)

| Delivery Day | Target Hours | Forecast Points (Cutoff) | Paired Actuals (A7) | Coverage | Selected Vintage Publish Time |
|---|---|---|---|---|---|
| **2026-01-01** | 24 | 24 | 24 | 100.0% | 2025-12-31 07:30:00Z |
| **2026-01-02** | 24 | 24 | 24 | 100.0% | 2026-01-01 07:30:00Z |
| **2026-01-03** | 24 | 24 | 24 | 100.0% | 2026-01-02 07:30:00Z |
| **2026-01-04** | 24 | 24 | 24 | 100.0% | 2026-01-03 07:30:00Z |
| **2026-01-05** | 24 | 24 | 24 | 100.0% | 2026-01-04 07:30:00Z |
| **2026-01-06** | 24 | 24 | 24 | 100.0% | 2026-01-05 07:30:00Z |
| **2026-01-07** | 24 | 24 | 24 | 100.0% | 2026-01-06 07:30:00Z |
| **2026-01-08** | 24 | 24 | 24 | 100.0% | 2026-01-07 07:30:00Z |
| **2026-01-09** | 24 | 24 | 24 | 100.0% | 2026-01-08 07:30:00Z |
| **2026-01-10** | 24 | 24 | 24 | 100.0% | 2026-01-09 07:30:00Z |
| **2026-01-11** | 24 | 24 | 24 | 100.0% | 2026-01-10 07:30:00Z |
| **2026-01-12** | 24 | 24 | 24 | 100.0% | 2026-01-11 07:30:00Z |
| **2026-01-13** | 24 | 24 | 24 | 100.0% | 2026-01-12 07:30:00Z |
| **2026-01-14** | 24 | 24 | 24 | 100.0% | 2026-01-13 07:30:00Z |
| **2026-01-15** | 24 | 24 | 24 | 100.0% | 2026-01-14 07:30:00Z |
| **2026-01-16** | 24 | 24 | 24 | 100.0% | 2026-01-15 07:30:00Z |
| **2026-01-17** | 24 | 24 | 24 | 100.0% | 2026-01-16 07:30:00Z |
| **2026-01-18** | 24 | 24 | 24 | 100.0% | 2026-01-17 07:30:00Z |
| **2026-01-19** | 24 | 24 | 24 | 100.0% | 2026-01-18 07:30:00Z |
| **2026-01-20** | 24 | 24 | 24 | 100.0% | 2026-01-19 07:30:00Z |
| **2026-01-21** | 24 | 24 | 24 | 100.0% | 2026-01-20 07:30:00Z |
| **2026-01-22** | 24 | 24 | 24 | 100.0% | 2026-01-21 07:30:00Z |
| **2026-01-23** | 24 | 24 | 24 | 100.0% | 2026-01-22 07:30:00Z |
| **2026-01-24** | 24 | 24 | 24 | 100.0% | 2026-01-23 07:30:00Z |
| **2026-01-25** | 24 | 24 | 24 | 100.0% | 2026-01-24 07:30:00Z |
| **2026-01-26** | 24 | 24 | 24 | 100.0% | 2026-01-25 07:30:00Z |
| **2026-01-27** | 24 | 24 | 24 | 100.0% | 2026-01-26 07:30:00Z |
| **2026-01-28** | 24 | 24 | 24 | 100.0% | 2026-01-27 07:30:00Z |
| **2026-01-29** | 24 | 24 | 24 | 100.0% | 2026-01-28 07:30:00Z |
| **2026-01-30** | 24 | 24 | 24 | 100.0% | 2026-01-29 07:30:00Z |
| **2026-01-31** | 24 | 24 | 24 | 100.0% | 2026-01-30 07:30:00Z |
| **Total** | **744** | **744** | **744** | **100.00%** | (31 days × 24 hours) |

---

## 6. Known Anomalies & Considerations for Downstream Modules

1. **Retrospective WINDFOR records:**
   Roughly 20.6% of WINDFOR rows have `startTime < publishTime`. The `by-horizon` module must ignore negative horizons or bucket only forward forecasts (`horizon_h >= 0`).
2. **Clock-time variation (2026-01-15):**
   One vintage was published at 12:25 UTC rather than the regular 11:30 UTC. The vintage selector must filter on `publishTime <= cutoff` rather than hardcoding clock schedules.
3. **Zero FUELHH missing periods:**
   National transmission-level wind actuals have no data gaps in January 2026. Coverage drops will only occur if user selects an extreme cutoff where no vintage was published before cutoff.
4. **Consistency of 07:30 UTC vintage:**
   At the default cutoff of 09:00 UTC on D-1, the selected vintage is uniformly the `07:30:00Z` vintage across all 31 days. Its forecast age is consistently 1.5 hours at decision time.
