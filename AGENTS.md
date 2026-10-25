# AGENTS.md — project rules for AI coding agents

Read this file first, every session. Then read `docs/SPEC.md`, `docs/DOMAIN.md`, `docs/PLAN.md`, `docs/TASKS.md` (in that order) before touching code.

## What we are building
A web app for the day-ahead power-buying team of a UK energy utility. It shows (1) the latest national wind generation forecast that was available at the moment they had to decide, and (2) how accurate those forecasts have been, in numbers, so they can price in the error. Data: Elexon BMRS only (FUELHH wind actuals, WINDFOR wind forecasts), January 2026.

Stack: React + TypeScript (Vite) frontend, Python 3.12 + FastAPI backend, Docker for local run, deployed on Vercel (Heroku container as fallback).
Hard limit: the whole assignment must fit in 16 hours. Prefer the simplest thing that meets `docs/SPEC.md`.

## How we work (non-negotiable)
1. **Spec before code.** If a task is not covered by SPEC/PLAN/TASKS, stop and propose a spec change first.
2. **One task at a time.** Take the next unchecked item in `docs/TASKS.md`. Do only that. Tick it only when its "Done when" is true.
3. **Verify, don't claim.** After each task run the checks in `docs/VERIFICATION.md` that apply, and paste the real output (tests, curl response, screenshot). "Looks done" is not done.
4. **Never invent API fields or numbers.** Inspect a real Elexon response and save it as a test fixture before writing parsers. Every number shown in the UI must trace to a tested function.
5. **Small commits.** One commit per task, message `type(scope): what` (e.g. `feat(api): add /accuracy/summary`). Work on short-lived branches or straight to `main` with green checks.
6. **Record decisions.** Any non-obvious choice (library, assumption, trade-off) goes in `docs/DECISIONS.md` as 3–5 lines.
7. **Log AI usage.** Keep `README.md` section "AI tools used" accurate (tool names, what they did, what was reviewed by hand).
8. **Keep context lean.** Read only the files you need. Do not paste whole data files into the chat; use head/summary commands.

## Conventions
- All timestamps are timezone-aware **UTC** internally and in the API (ISO 8601 with `Z`). Convert to Europe/London only for display labels.
- Units: MW (half-hourly average power). Never mix with MWh without saying so.
- Sign convention: `error_mw = forecast_mw - actual_mw` (positive = over-forecast = buyer under-procures). Used everywhere, labelled in plain English in the UI.
- Python: type hints everywhere, `ruff` for lint/format, `pytest`. Pure functions for analytics (no I/O inside metric code). Pydantic models for every API response.
- TypeScript: `strict` on, no `any`, data fetching via TanStack Query, API types generated from or mirrored to the OpenAPI schema.
- No secrets in the repo. The Elexon API needs no key.
- No data beyond Elexon FUELHH (WIND) and WINDFOR. Do not add weather, demand or price feeds.

## Commands (update this section as soon as the scaffold exists)
```
# backend
cd backend && uv sync (or pip install -r requirements.txt)
pytest -q
ruff check . && ruff format --check .
uvicorn app.main:app --reload

# frontend
cd frontend && npm ci
npm run dev | npm run build | npm run lint | npm test

# whole stack
docker compose up --build        # app on http://localhost:8080
```

## Definition of done (any task)
Code + tests + lint clean + verification evidence + TASKS.md ticked + commit. If UI: checked at 375px and 1280px widths, keyboard focus visible, loading/empty/error states present.

## Don'ts
- Don't refactor unrelated code. Don't add dependencies without a line in DECISIONS.md.
- Don't forward-fill or silently drop missing data; surface it (coverage numbers).
- Don't hide uncertainty: show data window, cutoff time and sample size next to every metric.
