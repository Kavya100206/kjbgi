# Vane — UK Wind Generation Decision & Accuracy Portal

Vane is an operational analytics portal built for the day-ahead power-procurement desk of a UK energy utility. It evaluates National Grid ESO wind forecasts published via Elexon BMRS against settlement outturn across January 2026. The platform reconstructs the exact latest forecast available at the decision cutoff, computes empirical forecast accuracy, and surfaces volumetric risk cushions so trading teams can price forecast bias and weather volatility cleanly into day-ahead procurement.

- **Live Application:** https://px9k2m.vercel.app
- **Local Portal:** http://localhost:8080
- **API Documentation:** https://px9k2m.vercel.app/api/docs (Local: http://localhost:8080/api/docs)

---

## Quickstart (Local Docker)

The application runs locally with a single command via Docker Compose (frontend Nginx reverse proxy + FastAPI backend):

```bash
docker compose up --build
```

Access the UI at `http://localhost:8080`.

### Running Tests

```bash
# Backend pytest suite (53 tests: unit, integration, AC-3 compliance, cross-check verification)
cd backend && uv run pytest -q

# Backend lint & format checks
uv run ruff check . && uv run ruff format --check .

# Frontend vitest suite (12 tests: formatters, URL-sync ControlStrip, mocked views)
cd frontend && npm test

# Frontend lint & production build
npm run lint && npm run build
```

### Re-running Ingest & Snapshot Verification

The repository includes a byte-identical, deterministic gzip snapshot of January 2026 Elexon BMRS data under `backend/data/snapshot/`. To re-fetch or refresh from the live Elexon API:

```bash
python scripts/ingest.py --refresh
python scripts/cross_check.py
python scripts/diagnostics.py
```

---

## Analytical Approach

1. **Vintages & Causal Cutoff:** Elexon WINDFOR forecasts are evaluated strictly by `publishTime`. For delivery hour $H$ on day $D$, Vane filters to the latest vintage published at or before the user's decision cutoff (default `09:00 UTC` on $D-1$). No future data leaks into decision curves.
2. **Hourly Pairing Rule (Assumption A7):** WINDFOR is published at hourly resolution; metered actuals (`FUELHH` with `fuelType == 'WIND'`) are reported per half-hour settlement period (:00 and :30). Hourly actual generation is computed as $\text{actual}_H = \frac{1}{2}(\text{FUELHH}_{H:00} + \text{FUELHH}_{H:30})$. If either half-hour is missing, the hour is excluded. Sensitivity analysis shows Option C vs Option A (H:00 only) alters MAE by $<0.7\%$ and bias by $<0.02\%$.
3. **Sign Convention:** $\text{error} = \text{forecast} - \text{actual}$. Positive error indicates over-forecast (shortfall volume; utility under-procures).
4. **Accuracy Metrics:** Calculated over complete January 2026 window ($n = 744$ hours, 100% coverage): MAE ($2,142\text{ MW}$), RMSE ($2,612\text{ MW}$), Mean Bias ($+1,852\text{ MW}$), and Normalized MAE ($18.5\%$).
5. **Systematic Bias Finding (+1,852 MW):** Day-ahead forecasts ran $+16.0\%$ above metered wind on 27 of 31 days ($87.1\%$). In Mean Squared Error decomposition, systematic bias accounts for $50.3\%$ of MSE ($\text{Bias}^2/\text{MSE}$), while $49.7\%$ is random meteorological variance. Unverified industry hypothesis: WINDFOR models total Great Britain wind generation (including distribution-embedded farms), whereas BMRS FUELHH meters transmission-connected Balancing Mechanism Units only. Vane preserves raw data without artificial calibration.
6. **Empirical Risk Cushion:** Quantiles (P10–P90, P05–P95) are derived empirically from historical decision residuals strictly prior to delivery day $D$, surfacing the required volume buffer in MW and stating how much is systematic bias.
7. **Honest Baseline:** Meteorological skill ($r = 0.9255$) achieves a $+51.3\%$ MAE reduction over the honest 48h causal persistence baseline ($4,184\text{ MW}$ MAE, $r = 0.2301$ on common $n=696$ sample).

---

## Directory Structure

```text
├── .github/workflows/ci.yml       # GitHub Actions CI workflow (lint + pytest + vitest + build)
├── api/index.py                   # Vercel serverless ASGI entrypoint
├── backend/                       # Python 3.12 FastAPI backend
│   ├── app/
│   │   ├── api/                   # REST routers (/forecast, /accuracy, /risk, /meta, /health)
│   │   ├── data/loader.py         # Snapshot data loader and indexer
│   │   ├── domain/                # Pure analytical models (pairing, vintage, metrics, risk)
│   │   └── main.py                # FastAPI application and CORS middleware
│   ├── data/snapshot/             # Compressed verified Elexon BMRS snapshot (113.7 KB)
│   ├── scripts/                   # Ingest and independent cross-check modules
│   └── tests/                     # 53 automated tests and raw Elexon test fixtures
├── docker-compose.yml             # Single-command local full-stack runner
├── docs/                          # Architecture decisions and diagnostic reports
│   ├── DECISIONS.md               # Architectural decision records (D-001 through D-008)
│   ├── DIAGNOSTICS.md             # Empirical bias diagnostics (time alignment, scale, stability)
│   └── screenshots/               # Portal UI captures (1280px desktop and 375px mobile)
├── frontend/                      # React 18 + TypeScript + Vite frontend
│   ├── src/
│   │   ├── api/                   # Typed API client and schema interfaces
│   │   ├── components/            # Header and URL-synced ControlStrip
│   │   ├── lib/                   # Numerical formatters and state hooks
│   │   ├── views/                 # DecisionView, AccuracyView, and MethodView
│   │   └── test/                  # Vitest component and formatter test suite
│   ├── Dockerfile                 # Multi-stage production build (Node builder -> Nginx runner)
│   └── nginx.conf                 # SPA static routing and /api reverse proxy
├── pyproject.toml                 # Root Python project configuration
├── requirements.txt               # Production Python runtime dependencies
├── scripts/                       # Local verification scripts (ingest, cross_check, diagnostics)
└── vercel.json                    # Serverless deployment configuration
```

---

## Limitations

1. **Fleet Scope Ambiguity:** Elexon BMRS does not disclose whether WINDFOR includes embedded generation or curtailment dispatch. While meteorological skill is proven ($r \approx 0.93$), physical fleet attribution remains an unverified hypothesis.
2. **Missing Intraday Adjustments:** Vane models day-ahead decision points only; it does not model intraday trading or BM cashout imbalance pricing.
3. **Historical Horizon:** Ingested snapshot covers January 2026. Seasonal shifts (summer wind output) will exhibit different quantile characteristics.

---

## AI Tools Used

This project was built with assistance from **Google Antigravity** using `[MODEL_PLACEHOLDER: e.g. Gemini 3.8 Flash (High)]`.

- **Role of AI:** Assisted with boilerplate scaffolding, test fixture parsing, typing, and initial drafting of domain calculations.
- **Human Verification:** All mathematical formulations (Assumption A7 pairing, empirical quantile calculations, MSE decomposition), API contracts, edge-case assertions (AC-3 vintage cutoff), and empirical diagnostic findings were independently validated against raw Elexon data and verified via independent cross-check modules.
