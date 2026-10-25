# PLAN — architecture and approach

## 1. Principles
Boring, testable, small. Heavy work happens offline (ingest). The runtime app serves a committed snapshot, so reviewers never hit Elexon and the demo is deterministic. Analytics are pure functions with tests. The API is thin. The UI renders what the API returns, no business logic in React.

## 2. Architecture
```
  Elexon BMRS API (offline, once)
        │  scripts/ingest.py  (chunked, retried, validated)
        ▼
  backend/data/snapshot/  actuals.csv.gz  forecasts.csv.gz  meta.json
        │  loaded once at startup
        ▼
  backend/app/
    config.py        window, default cutoff, constants
    data/loader.py   read + validate snapshot into typed frames
    domain/pairing.py  A7 hourly pairing: mean two 30-min FUELHH halves per target hour
    domain/vintage.py  select forecast-at-cutoff, compute horizons
    domain/metrics.py  MAE, RMSE, bias, nMAE, quantiles (pure)
    domain/risk.py     empirical error bands (prior days only)
    api/routes_*.py    FastAPI routers, Pydantic response models
    main.py            app factory, CORS, /api/health
        │  JSON over HTTP  (/api/*)
        ▼
  frontend/src/
    api/        typed client + TanStack Query hooks
    views/      DecisionView, AccuracyView, MethodView
    components/ ForecastChart, ErrorHistogram, KpiRow, ControlStrip, ...
    lib/        formatters (UTC→London labels, MW, %)
```

## 3. Repo layout (target)
```
/ (repo root, anonymous name)
├─ README.md   AGENTS.md
├─ docs/       SPEC, DOMAIN, PLAN, TASKS, VERIFICATION, DECISIONS, DELIVERABLES
├─ backend/    app/  tests/  scripts/ingest.py  data/snapshot/  pyproject.toml  Dockerfile
├─ frontend/   src/  index.html  package.json  vite.config.ts  Dockerfile  nginx.conf
├─ api/        index.py            # Vercel entry that exposes backend.app.main:app
├─ docker-compose.yml   vercel.json   .github/workflows/ci.yml
```

## 4. API contract (all UTC ISO-8601; all responses Pydantic-typed; OpenAPI at /api/docs)
| Endpoint | Query | Returns |
|---|---|---|
| GET /api/health | – | status, version |
| GET /api/meta | – | window, ingest time, row counts, default cutoff, list of delivery dates |
| GET /api/forecast/day | date, cutoff_hour | **24 rows** (one per WINDFOR target hour): start_time, forecast_mw, forecast_publish_time, forecast_age_h, actual_mw? (hourly mean per A7); day summary (peak, mean, min, n_missing, selected_vintage_publish_time) |
| GET /api/forecast/revisions | target (start_time) or date | vintages: publish_time, forecast_mw, horizon_h, plus the actual |
| GET /api/accuracy/summary | from, to, cutoff_hour | MAE, RMSE, bias, nMAE, P90/P95 abs error, worst over-forecast, n, coverage |
| GET /api/accuracy/by-horizon | from, to | bucketed metrics over **all vintages** (no cutoff_hour — purpose is to show how accuracy decays with lead time; distinct from all other accuracy endpoints which use only the forecast-at-cutoff vintage) |
| GET /api/accuracy/by-hour | from, to, cutoff_hour | 24 rows of metrics |
| GET /api/accuracy/daily | from, to, cutoff_hour | per-day MAE, bias, n |
| GET /api/accuracy/distribution | from, to, cutoff_hour, bins | histogram bins + quantiles |
| GET /api/risk/band | date, cutoff_hour, confidence | per-period forecast, lo, hi, cushion_mw, history_days_used, fallback flag |

Validate params (dates within window, cutoff 0–23, from ≤ to) with clear 422 messages.

## 5. Key technical decisions (record the final answers in DECISIONS.md)
- **Snapshot not live calls.** Deterministic, fast, no outage risk. A `--refresh` flag in ingest keeps it repeatable and honest about provenance.
- **Snapshot format.** Plain CSV.gz in git (`actuals.csv.gz`, `forecasts.csv.gz`). Total estimated size ~140 KB gzipped — well within git limits, no LFS needed.
- **Ingest strategy.** FUELHH: `settlementDateFrom/To`, one request for the full window (32 days, 1,536 rows). WINDFOR: `publishDateTimeFrom/To` only (settlementDate params return live forecast, not historical), chunked at 7-day windows with 0.5 s delay between requests.
- **Data engine.** Start with pandas + numpy. Measure the Vercel function bundle; limit is 250 MB unzipped. If it is too big, switch runtime analytics to plain numpy or precompute per-cutoff aggregates (24 cutoffs × small tables) at build time.
- **Hosting.** Vercel monorepo: frontend as static build, FastAPI as a Python function at `/api/*` via `vercel.json` rewrites. Heroku container deploy (single multi-stage Dockerfile serving both) is the fallback. **Decision rule for T0.6 (hard time-box 30 min):** if the Vercel spike (hello-world FastAPI + pandas import + bundle size check) fails for any reason OR the compressed bundle exceeds Vercel's documented limit, stop and switch to the Heroku container path immediately. Do not keep fighting Vercel. Record both the documented limits and measured sizes in DECISIONS.md.
- **Docker.** `docker compose up` runs backend + frontend (nginx proxying /api). Local parity with production routes.
- **Charts.** Recharts (ComposedChart: line for forecast, line for actual, area for band). Keep to one chart library.
- **State.** URL query params hold date/cutoff/range so any view is linkable and reproducible in the demo.
- **Testing.** pytest (+ hypothesis for vintage selection invariants if time), Vitest + Testing Library, optional Playwright smoke test on the deployed URL.
- **CI.** GitHub Actions: ruff, pytest, eslint, tsc, vitest, frontend build, docker build. No live network in CI.

## 6. Phases, time budget (target ≤ 14h, 2h buffer), exit criteria
| Phase | Hours | Exit criteria |
|---|---|---|
| 0 Scaffold and CI | 1.0 | Repos, tooling, empty app runs in Docker, CI green |
| 1 Data ingest | 2.5 | Snapshot committed; row counts and date coverage report printed; raw fixtures saved; findings noted in DOMAIN.md |
| 2 Domain logic | 2.5 | vintage, metrics, risk modules with tests; independent cross-check of numbers |
| 3 API | 1.5 | All endpoints, typed, tested, documented at /api/docs |
| 4 Frontend | 4.0 | Three views working against local API, responsive, states handled, tested |
| 5 Deploy | 1.0 | Public URL passes incognito check; Dockerfile and compose verified from clean clone |
| 6 Docs and video | 1.5 | README complete; both video parts recorded and uploaded unlisted; form submitted |
Cut order if time is short: FR-9 → FR-7 polish → Playwright → hypothesis tests. Never cut: FR-1…FR-6, FR-10, tests on vintage and metrics.

## 7. Risks and mitigations
| Risk | Mitigation |
|---|---|
| API parameters/shape differ from docs | Phase 1 starts with exploration + saved fixtures; update DOMAIN.md |
| Look-ahead bias in "latest forecast" | Vintage module is the only way to get forecasts; tests on boundary cases |
| Vercel Python bundle too large / cold start slow | Measure early (Phase 0 spike), fall back to precompute or Heroku container |
| Ambiguity in "decisions in January" | A1/A2 documented, configurable, explained in Method page and video |
| Scope creep | SPEC priorities, cut order above, TASKS discipline |
| Chart legibility with 744 points × vintages | Aggregate/limit revisions chart to selected target or day; downsample only in the view, never in metrics |
| WINDFOR hourly vs FUELHH 30-min granularity | A7 pairing rule: mean two FUELHH halves per hour; exclude if either missing; sensitivity check in T2.5 |
