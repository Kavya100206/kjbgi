# DECISIONS — lightweight decision log
Format: date · decision · why · alternatives · consequence. Keep each to 3–5 lines. Add as you go.

## D-001 Serve a committed snapshot, not live Elexon calls
Why: deterministic demo, no rate-limit/outage risk for reviewers, fast. Alternative: live fetch with cache (more moving parts). Consequence: ingest script must be re-runnable and documented.

## D-002 Decision cutoff is a configurable assumption (default 09:00 UTC on D-1)
Why: the brief says "one day before delivery" without a time; the market has real cutoffs we choose not to model. Consequence: UI states the assumption; cutoff selector drives all numbers.

## D-003 Error sign: forecast − actual
Why: positive = over-forecast = buyer risk. Consequence: all labels explain it in plain English.

## (add more below: hosting choice after T0.6, pandas vs numpy, chart library, any spec deviations)

## D-004 Hourly pairing rule (Option C chosen over A and B)
Why: WINDFOR is hourly, FUELHH is 30-min. Option A (H:00 only) ignores half the actual data. Option B (WINDFOR repeated for :30) invents data. Option C (mean of H:00 and H:30) uses all FUELHH data without fabricating forecast points. Limitation: unknown whether WINDFOR value is an hour-average or instantaneous. Sensitivity (Option A vs C diff) computed in T2.5 and pasted here when available. Consequence: denominator = 744 (24 h × 31 days); hours with either half missing are excluded.

## D-005 Vintage selection uses real publishTime from WINDFOR
Why: WINDFOR publish clock times are mostly regular (02:30, 04:30, 07:30, 09:30, 11:30, 15:30, 18:30, 22:30 UTC) but one exception observed (12:25 instead of 11:30). Do not hardcode clock times. Use actual `publishTime` values from the snapshot. Consequence: vintage selection is always exact, never approximated from a schedule.

## D-006 Jan-1 coverage confirmed; ingest starts 2025-12-29
Why: B4 concern was that WINDFOR might not have Dec 29 data. T1.1 confirmed: earliest publishTime in snapshot is 2025-12-29T02:30:00Z. For Jan 1 at 09:00 cutoff (D-1 = Dec 31T09:00Z), the latest eligible vintage is 2025-12-31T07:30:00Z — all 24 Jan 1 target hours have coverage. Consequence: ingest window Dec 29–Jan 31 is sufficient; no coverage gap on Jan 1 at the default cutoff.
