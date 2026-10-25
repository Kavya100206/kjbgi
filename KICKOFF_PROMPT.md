# Kickoff prompt — paste this as the first message in Antigravity

You are the lead engineer on a 16-hour take-home project. Work like a senior engineer: spec first, small verified steps, evidence over claims.

1. Read, in order: `AGENTS.md`, `docs/SPEC.md`, `docs/DOMAIN.md`, `docs/PLAN.md`, `docs/TASKS.md`, `docs/VERIFICATION.md`. (Use planning mode if available.)
2. Reply with: (a) your understanding of the problem in 5 lines, (b) any contradictions or gaps you found in the docs, (c) the risks you see in the PLAN. Do NOT write code yet.
3. After I approve, start at the first unchecked task in `docs/TASKS.md`. For each task:
   - restate the "Done when" criteria,
   - implement only that task,
   - run the applicable checks from `docs/VERIFICATION.md` and show the real output,
   - tick the task, commit, and stop for my review before the next phase boundary.
4. Phase 1 (data) is the riskiest. Before writing parsers, call the real Elexon endpoints, save raw samples under `backend/tests/fixtures/`, and tell me what fields/shapes you actually saw, including anything that differs from `docs/DOMAIN.md`.
5. If something in the docs is wrong or impossible, propose the change and update the doc; don't silently deviate.
