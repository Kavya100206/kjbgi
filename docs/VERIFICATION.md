# VERIFICATION — how we prove each thing works

Rule: evidence beats claims. After each task, run the relevant checks and paste the actual output.

## 1. Automated checks (run before every commit)
```
backend:  ruff check . && ruff format --check . && pytest -q
frontend: npm run lint && npx tsc --noEmit && npm test -- --run && npm run build
stack:    docker compose build
```

## 2. Must-have test cases

### Pairing (backend/tests/test_pairing.py)
Verify `domain/pairing.py` — hourly actual = mean(FUELHH H:00, H:30) per A7:
- Both half-hours present → `actual_hourly = mean(gen_00, gen_30)` exact.
- H:00 missing → hour excluded, counted in coverage gap.
- H:30 missing → hour excluded, counted in coverage gap.
- Both missing → hour excluded.
- Boundary hours: 00:00 (midnight) and 23:00 produce correct means.
- A full 24-hour day with complete data returns exactly 24 rows with `coverage_ok=True`.
- A day with one gap returns 23 rows and reports 1 coverage gap.

- Forecast published exactly at cutoff is **included**; one second later is **excluded**.
- Several vintages for one target: the latest ≤ cutoff wins.
- No vintage ≤ cutoff: target is dropped and counted in coverage, not filled.
- Target on the first day of the window uses a forecast published the previous calendar day.
- Changing cutoff hour changes the selected vintage as expected.
- Horizon = startTime − publishTime in hours, exact for a known pair.

### Metrics (backend/tests/test_metrics.py)
Use a tiny fixture with hand-computed answers, e.g. forecast = [10, 20, 30], actual = [12, 18, 33]:
errors = [−2, +2, −3] → MAE = 7/3 ≈ 2.3333, RMSE = sqrt(17/3) ≈ 2.3805, bias = −1.0, nMAE = MAE / mean(actual) = 2.3333/21 ≈ 11.11%.
**Note:** under the sign convention `error = forecast − actual`, bias = −1.0 means the forecast was on average **lower** than actuals — this is a **net under-forecast** example. Verify tests use the correct sign; a positive bias means over-forecast (buyer risk).
- Empty input returns defined nulls, not exceptions or NaN in JSON.
- Quantile method documented and tested at p = 0, 0.5, 1.
- Sign convention test: over-forecast yields positive error.

### Risk band (backend/tests/test_risk.py)
- For day D only errors from days < D are used (assert by constructing data where later days have extreme errors).
- Fewer than 3 history days sets `fallback = true`.
- Band lower bound never < 0 MW.

### Ingest (backend/tests/test_ingest.py)
- Parsers handle saved real fixtures; unknown/missing fields raise clear errors.
- Dedupe keeps latest `publishTime`.
- No live network calls in tests (use fixtures / httpx mock).

### API (backend/tests/test_api.py)
- `GET /api/forecast/day?date=2026-01-15&cutoff_hour=9` returns 48 rows; every `forecast_publish_time` ≤ 2026-01-14T09:00:00Z.
- Out-of-window date returns 422 with a helpful message.
- Summary numbers equal the independent cross-check script output (T2.5).

### Frontend
- Formatters: UTC → London label, MW rounding, % formatting.
- ControlStrip updates URL and re-queries.
- A view renders loading, error, empty and data states from mocked responses.

## 3. Independent cross-check (T2.5)
A separate script written in plain pandas, not importing `app.domain`, recomputes headline metrics for all January at cutoff 09:00 using:
1. **Option C pairing** (A7: mean of H:00 and H:30 FUELHH) — must match app API/summary to 1e-6.
2. **Option A pairing** (H:00 actual only, no averaging) — compute MAE and bias; report the difference from Option C.
Paste both outputs (Option C and sensitivity diff) in DECISIONS.md D-004.

## 4. Data sanity checks (on snapshot)
- Actuals: 1,488 periods expected for 31 days; list any gaps.
- Values are non-negative MW and within a plausible range for GB wind; list outliers instead of dropping them.
- Forecast publish times are monotonic per file chunk; show horizon min/median/max.

## 5. UI QA checklist
- 375px and 1280px: no horizontal scroll, charts readable, controls reachable.
- Keyboard: tab order logical, focus ring visible, chart info also available as a table or text summary.
- Colour contrast ≥ 4.5:1 for text; forecast vs actual distinguishable without colour (line style differs).
- Every metric shows window, cutoff and n. Units shown.
- Loading, empty and error states present and explain next steps.
- Reduced-motion respected. No layout shift when data arrives.

## 6. Deployed smoke test (incognito window)
1. Open the public URL: UI loads, no login, no console errors.
2. `/api/meta` returns the January 2026 window and ingest time.
3. Decision view for 2026-01-15 at 09:00 matches local numbers.
4. Accuracy view headline equals local numbers.
5. Reload with query params preserved. Mobile viewport OK.
6. Repeat for GitHub repo URL and YouTube URL (unlisted video plays logged out).
