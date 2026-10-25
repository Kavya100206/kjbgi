# SPEC — Wind forecast decision & accuracy portal

## 1. Context
Client: a UK energy utility. The day-ahead buying team must buy, one day before delivery, the power their customers will need beyond what wind will supply. Wind output is weather-dependent, so they rely on forecasts. We are delivering a first version (pilot) of a web portal, pitched to the client and reviewed by an internal tech lead.

## 2. Users and jobs to be done
| User | Job |
|---|---|
| Day-ahead trader / buyer | "What does the latest wind forecast say for tomorrow, as of my decision time?" |
| Same, plus risk lead | "How wrong has that forecast been, and how much should I cushion for it?" |
| Internal tech lead (reviewer) | "Can I understand, run and trust this codebase quickly?" |

## 3. Scope
**In:** national-level wind actuals (FUELHH, fuelType WIND) and wind forecasts (WINDFOR) from Elexon BMRS; January 2026; forecast viewer; accuracy analytics; deployed web app; Docker; tests; README; demo video.
**Out:** any other data source, demand or price data, user accounts, live/real-time refresh, forecasting models of our own, other fuel types, regional data.

## 4. Assumptions (each is configurable and shown in the UI "Method" page)
- **A1 Window.** Delivery (target) periods with `startTime` in 2026-01-01 00:00Z … 2026-01-31 23:30Z. Ingest a slightly wider range (actuals to 2026-02-01, forecasts published from 2025-12-29) so every January target can have its D-1 forecast. Changing the window is one constant.
- **A2 Decision cutoff.** The buyer decides on day D-1 at a cutoff time, default **09:00 UTC (= UK time in January)**. For a target `t` on delivery day D the "forecast at decision time" is the forecast with the **latest `publishTime` ≤ cutoff(D-1)** for that `startTime`. Cutoff hour is user-selectable (00–23). This is a modelling choice, not a market rule; say so in the UI.
- **A3 Sign convention.** `error = forecast − actual` (positive = over-forecast = risk of buying too little).
- **A4 Missing data.** If no forecast exists at/before cutoff for a target, that target is excluded from metrics and counted in a visible "coverage" figure. No forward-fill.
- **A5 No demand data.** We do not compute procurement volumes. We quantify wind uncertainty (MW) the buyer can apply to their own demand numbers.
- **A6 Deduplication.** If the source returns several rows for the same key (e.g. FUELHH re-publications), keep the latest `publishTime`; exact duplicates are dropped.

## 5. Functional requirements
Priority: P0 = must, P1 = should, P2 = if time remains.

| ID | Pri | Requirement |
|---|---|---|
| FR-1 | P0 | Ingest FUELHH (WIND) and WINDFOR for the window via a repeatable script; store a compact snapshot in the repo; record ingest time and row counts. |
| FR-2 | P0 | **Decision view:** pick a delivery day and cutoff hour. Show a 48-period chart of the forecast at decision time, each point carrying the `publishTime` of the forecast used. Show actuals overlaid when they exist, **clearly labelled "Known only after delivery" — actuals are hindsight and were not available to the buyer at decision time.** Never imply the actuals were known at cutoff. |
| FR-3 | P0 | **Forecast revisions:** for a chosen target period (or the day), show how the forecast changed across publish times, so users see how stale/fresh the decision-time forecast was. |
| FR-4 | P0 | **Accuracy summary** for a date range + cutoff: MAE, RMSE, mean error (bias), normalised MAE (% of mean actual), P90/P95 absolute error, worst over-forecast, coverage (n used / n total). |
| FR-5 | P0 | **Accuracy breakdowns:** by forecast horizon (hours between publish and target), by hour of day, and by day. |
| FR-6 | P0 | **Error distribution:** histogram of errors plus quantiles, with plain-English reading ("on 1 in 10 half-hours the forecast was too high by ≥ X MW"). |
| FR-7 | P1 | **Risk buffer:** for a delivery day, show forecast with an empirical error band (e.g. P10–P90 or chosen confidence) and the MW cushion implied. Computed from prior days only to avoid look-ahead; fall back flagged when history < 3 days. |
| FR-8 | P1 | **Method & data page:** assumptions A1–A6, definitions and formulas, data provenance, ingest timestamp, known limitations. Must include: (a) actuals overlay is hindsight — it shows what happened, not what was known; (b) FUELHH and WINDFOR may not cover the same wind fleet (embedded wind hypothesis); (c) coverage < 100% when no forecast exists at/before cutoff; (d) by-horizon view uses all vintages, not the cutoff-filtered set. |
| FR-9 | P2 | What-if: user enters a flat demand figure (MW) and sees residual need = demand − forecast with the buffer. |
| FR-10 | P0 | Public deployed URL; Docker setup; README per `docs/DELIVERABLES.md`. |

## 6. Non-functional requirements
- **Correctness:** metric functions unit-tested against hand-computed fixtures; vintage selection tested on boundary cases.
- **Performance:** every endpoint < 500 ms warm on the deployed instance; first paint < 3 s on broadband.
- **Reliability:** the app never calls Elexon at request time; it serves the committed snapshot (deterministic, no rate-limit or outage risk during review).
- **Usability:** a trader understands each screen without explanation; units and cutoff always visible; plain-language labels; works at 375px and 1280px; keyboard accessible; colour is not the only carrier of meaning.
- **Maintainability:** typed code, small modules, CI on every push, README lets a stranger run it in under 5 minutes.
- **Security/privacy:** no secrets, no user data, CORS restricted to the app origin, dependencies pinned.

## 7. Acceptance criteria (the reviewer's checklist)
1. `docker compose up --build` serves the app locally; the README steps work from a clean clone.
2. Deployed URL loads in an incognito window with no login and shows January 2026 data.
3. For delivery day 2026-01-15 at cutoff 09:00, the app shows 48 forecast points, each using a forecast published ≤ 2026-01-14 09:00Z.
4. Accuracy summary numbers match an independent calculation in the test suite (pandas notebook or script) to 1e-6.
5. Changing the cutoff hour changes the selected forecasts and the metrics, and the UI says what changed.
6. Tests and lint pass in CI; CI badge/log visible.
7. The video fits 10 minutes and covers both parts in `docs/DELIVERABLES.md`.

## 8. UI direction (brief)
Subject: a trading-desk tool for energy buyers who scan quickly and distrust vague claims. Aesthetic: calm, precise, data-first; the chart is the hero. Make deliberate choices, not template defaults.
- Palette (named tokens, adjust if contrast fails): `ground #EDF1F4`, `ink #12253A`, `wind #0F7C86` (forecast), `actual #D98E04` (actuals), `risk #B83A3A` (over-forecast / shortfall), `band #0F7C86` at 15% opacity.
- Type: two families. UI and numbers: Public Sans with tabular figures. Titles and explanatory copy: Newsreader. Sentence case, no all-caps eyebrows.
- Layout: left-aligned; persistent control strip (delivery day, cutoff hour, date range) above three views: Decision, Accuracy, Method. KPIs as a compact row, not identical card grids.
- Every metric shows its window, cutoff and n. Empty/error/loading states explain what to do.
- Spend boldness in one place: the decision chart with forecast, band and actuals, with the forecast age visible on hover.
