# DELIVERABLES — README, video, submission

## README.md must contain (reviewer reads this first)
1. One-paragraph summary and screenshot.
2. **Live app link** (Vercel/Heroku) and video link.
3. **How to run:** prerequisites, `docker compose up --build`, URL, how to run tests, how to re-run ingest.
4. **Files and directories:** annotated tree (what each folder/file is for).
5. **Approach in 10 lines:** vintages, cutoff, metrics, risk band, key assumptions A1–A6.
6. **AI tools used:** name each tool (Antigravity, and any model used inside it, plus any chat assistants), what it was used for (scaffolding, tests, docs), and what was reviewed or written by hand. Be explicit and honest.
7. Limitations and next steps.

## Video (unlisted YouTube, ≤ 10 min total; evaluators watch this first)
### Part 1 — Customer pitch (≈4:30). Audience: head of day-ahead desk. Goal: impress.
- 0:00 Problem in their words: you must commit tomorrow's volumes before you know tomorrow's wind. (20 s)
- 0:20 What we built: one screen shows what the forecast said *when you had to decide*, another says how wrong it tends to be. (20 s)
- 0:40 Live demo, Decision view for a windy day in January: forecast at 09:00 cutoff, forecast age, actual outcome overlay, the cushion band. Say the MW and what it means in £-risk terms qualitatively, no invented prices. (90 s)
- 2:10 Accuracy view: headline MAE / bias / P90 over-forecast; accuracy by lead time (why using the right vintage matters); by hour of day. Give one concrete insight you found in the data. (120 s)
- 4:10 How they'd use it Monday morning, and what a next phase could add (their own demand, more fuel types, live refresh). Close with the ask. (20 s)
### Part 2 — Tech review (≈4:30). Audience: tech lead. Goal: easy review, knowledge transfer.
- 0:00 Architecture diagram: offline ingest → snapshot → pure domain modules → thin API → React views. Why snapshot. (60 s)
- 1:00 The core idea in code: vintage selection and why look-ahead bias would flatter the forecast; show the test. (90 s)
- 2:30 Metrics and risk band: definitions, sign convention, independent cross-check result. (60 s)
- 3:30 Practices: types, tests count, CI, Docker, decisions log, how AI tools were used and verified. (45 s)
- 4:15 Trade-offs, known limitations, what you'd do next, how to run it. (15–30 s)
Recording tips: 1080p, rehearse twice, script the demo clicks, keep URL params so views load instantly, hide notifications, narrate the "why" not the "what". Use the 10-minute cap as a hard budget; cut Part 1 or 2 evenly if over.

## Repo checklist
- [ ] Public GitHub repo with anonymous random name (e.g. `kjhwr`), no personal name in code, README author line, git author, or commit history that you don't want public.
- [ ] No secrets, large junk, or .env committed. Snapshot size reasonable.
- [ ] README complete; CI green.

## Submission form checklist ("Full Stack SWE challenge submission v4")
- [ ] Open **each** URL (app, repo, video) in an incognito window and confirm access without login.
- [ ] Video is **unlisted** (not private), and plays to the end.
- [ ] Re-read form fields; paste final URLs; submit; keep a screenshot of the confirmation.
