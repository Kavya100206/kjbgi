# TASKS — work top to bottom. Tick only when "Done when" is true and evidence is shown.

## Phase 0 — Scaffold and CI (≈1h)
- [x] T0.1 Create repo skeleton per PLAN §3; add AGENTS.md and docs/. Done when: tree matches, first commit made.
- [x] T0.2 Backend scaffold: FastAPI app, `/api/health`, pyproject, ruff, pytest with one passing test. Done when: `pytest -q` green, `curl /api/health` returns ok.
- [x] T0.3 Frontend scaffold: Vite + React + TS strict, eslint, Vitest with one passing test, TanStack Query, router. Done when: `npm run build && npm test` green.
- [x] T0.4 Docker: backend Dockerfile, frontend Dockerfile + nginx proxy, docker-compose. Done when: `docker compose up --build` serves UI at :8080 and health via the proxy.
- [ ] T0.5 CI workflow (lint, test, build, docker build). Done when: green run on GitHub.
- [x] T0.6 Vercel spike (time-box 30 min): deploy a hello-world FastAPI function + static page, import pandas, check bundle size (both compressed AND unzipped). Look up current Vercel Python function limits from docs before measuring. Done when: DECISIONS.md records "Vercel OK" or "fallback to Heroku container" with documented limits and measured sizes. If spike fails or exceeds limits, switch to Heroku immediately.

## Phase 1 — Data ingest (≈2.5h)
- [x] T1.1 Explore both Elexon endpoints with small windows; save raw JSON under `backend/tests/fixtures/`. Done when: DOMAIN.md "To verify" list is answered with what was observed. ✓ Completed 2026-10-26: fixtures saved, DOMAIN.md updated with confirmed fields.
- [x] T1.2 `scripts/ingest.py`: chunked fetch (7-day chunks, 0.5 s delay) with retry/backoff, pydantic validation, dedupe (A6), UTC parsing, window from config (A1). FUELHH uses `settlementDateFrom/To`; WINDFOR uses `publishDateTimeFrom/To` only. Done when: runs end to end with `--refresh`, idempotent.
- [x] T1.3 Write snapshot (`actuals.csv.gz`, `forecasts.csv.gz`, `meta.json` with ingest time, counts, min/max times). Done when: committed, total size reported (expected ~140 KB gzipped).
- [x] T1.4 Data quality report: vintages per day (expected 8), horizon min/median/max for WINDFOR, count of hours missing a half-hour actual (FUELHH gaps), Jan 1 coverage at 09:00 cutoff (expected: 24 of 24 hours covered), full coverage table 24×31=744 hours. Done when: report saved to `docs/DATA_REPORT.md` and anomalies listed.
- [x] T1.5 Loader module with schema validation and tests using fixtures. Done when: tests green, loader fails loudly on bad schema.

## Phase 2 — Domain logic (≈2.5h)
- [x] T2.0 `domain/pairing.py`: hourly actual = mean of FUELHH H:00 and H:30; exclude hour if either missing; return paired DataFrame with coverage flag. Done when: tests cover (a) both halves present → correct mean, (b) one half missing → excluded, (c) both missing → excluded, (d) boundary hours 00:00 and 23:00, (e) 24 rows per delivery day when data is complete.
- [x] T2.1 `vintage.py`: forecast-at-cutoff selection and horizon calc. Done when: tests cover exact-equal cutoff, none-before-cutoff, multiple vintages, day boundary, cutoff hour change.
- [ ] T2.2 `metrics.py`: MAE, RMSE, bias, nMAE, quantiles, coverage. Done when: hand-computed fixture test passes, empty/NaN cases defined.
- [ ] T2.3 By-horizon, by-hour, daily, distribution aggregations. Done when: tests green; totals reconcile with summary.
- [ ] T2.4 `risk.py`: prior-days-only empirical bands with fallback flag. Done when: test proves no use of same-day or later errors.
- [ ] T2.5 Independent cross-check: a separate script (plain pandas, different code path) recomputes the headline metrics for Jan at 09:00 cutoff using Option C pairing AND Option A (H:00 only) pairing. Done when: Option C matches app metrics to 1e-6; sensitivity diff (MAE and bias difference between A and C) pasted into DECISIONS.md.

## Phase 3 — API (≈1.5h)
- [ ] T3.1 Routers + Pydantic models for all endpoints in PLAN §4 with validation. Done when: OpenAPI complete, 422s clear.
- [ ] T3.2 API tests (TestClient) incl. acceptance criterion 3 (day 2026-01-15, 09:00, 24 rows, all publish_times ≤ 2026-01-14T09:00Z). Done when: green.
- [ ] T3.3 CORS, error handler, caching headers for static data. Done when: manual curl checks pasted.

## Phase 4 — Frontend (≈4h)
- [ ] T4.1 Design tokens, fonts, layout shell, ControlStrip with URL-synced state. Done when: reload keeps state, 375px and 1280px screenshots OK.
- [ ] T4.2 Decision view: ForecastChart (forecast, actual, band), day summary, forecast-age hover, selected vintage publishTime visible. Done when: matches API numbers for 2026-01-15.
- [ ] T4.3 Revisions panel (vintage evolution for selected target/day). Done when: shows publish times and values correctly.
- [ ] T4.4 Accuracy view: KPI row, by-horizon chart, by-hour chart, daily chart, error histogram with plain-English reading. Done when: numbers equal API/summary.
- [ ] T4.5 Method view: assumptions A1–A7, formulas, data provenance, limitations (incl. A7 pairing and sensitivity). Done when: every A1–A7 appears.
- [ ] T4.6 Loading, empty, error states; keyboard focus; contrast check. Done when: checklist in VERIFICATION §5 passes.
- [ ] T4.7 Frontend tests: formatters, ControlStrip, one view with mocked API. Done when: green in CI.

## Phase 5 — Deploy (≈1h)
- [ ] T5.1 Deploy to chosen host per T0.6 decision. Done when: public URL serves UI and /api/meta.
- [ ] T5.2 Incognito verification of every URL to be submitted. Done when: checked and noted.
- [ ] T5.3 Clean-clone test: fresh clone → README steps → `docker compose up` works. Done when: confirmed.

## Phase 6 — Docs and video (≈1.5h)
- [ ] T6.1 README per `docs/DELIVERABLES.md` incl. AI-tools disclosure and deployed link.
- [ ] T6.2 Rehearse and record video (two parts, ≤ 10 min), upload unlisted, verify in incognito.
- [ ] T6.3 Anonymise repo name, make public, check no personal info/secrets in history.
- [ ] T6.4 Fill and submit the form; re-verify every link in incognito.

## Stretch (only if all P0/P1 done)
- [ ] S1 FR-9 what-if calculator.  - [ ] S2 Playwright smoke on deployed URL.  - [ ] S3 hypothesis property tests for vintage selection.
