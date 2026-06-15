---
description: Retrospective — turn this session's friction into durable repo improvements (the compounding loop)
argument-hint: "[optional focus area, e.g. 'wiktionary parsing' or 'test setup']"
---

You just finished a task in this Anki addons monorepo. Run a **compounding-loop
retrospective** so the next task here is closer to one-shot. Be honest and concrete,
and prefer patching the repo over re-explaining things in chat.

Work through these steps:

1. **Diagnose the friction.** Look back over THIS session and name the specific
   things that cost tokens or caused back-and-forth: wrong guesses, missing
   context, repeated verification, commands you had to discover, knowledge you
   re-derived from scratch, edits that matched the wrong site, tests run from the
   wrong directory. Quote concrete moments — don't generalize.
   If `$ARGUMENTS` is non-empty, focus the retrospective there.

2. **Map each friction point to a principle and a durable artifact.** Principles to
   apply: _fast scoped verification_ (a cheap command that proves the change),
   _knowledge capture_ (write it down once, version-controlled), _edit precision_
   (unique anchors so edits land at the right site), _cache-stable context_ (don't
   churn auto-loaded files), and _the compounding loop_ (today's correction should
   be impossible to need next month). For each friction point, name the artifact
   that would have prevented it, choosing from what this repo actually uses:
   - a knowledge doc under `docs/` (cross-cutting how-tos, gotchas, pipelines);
   - a test under the relevant `<addon>/tests/` or the root `tests/` (per-addon
     behavior is captured as a test, TDD-style — see how `auto_wiktionary/tests/`
     pin redirect corner cases);
   - a `Makefile` target (verification, data pipeline, lint/format);
   - a lint/CI gate under `.github/workflows/`;
   - behavioral guidance in a `.jules/*.md` persona, if it's about _how an agent
     should work_ rather than repo facts;
   - a small `CLAUDE.md` at the repo root — **only** if the rule is broadly useful
     and stable. There is none today; create one sparingly, since it becomes
     auto-loaded context for every future session.

3. **Check what already exists first.** Before adding anything, read the relevant
   `Makefile` targets, `conftest.py`, `docs/`, `.jules/*.md`, `.github/workflows/`,
   and the addon's own `tests/`. Patch real gaps instead of duplicating. Don't put
   repo knowledge in chat or memory if it belongs in a version-controlled file.

   Repo facts worth respecting (and worth documenting if you re-learned them):
   - **Run checks and tests from the repo root.** The root `conftest.py` mocks
     `aqt`/`anki`; running `pytest` inside an addon subdir fails to import those.
     Scoped run: `python3 -m pytest <addon>/tests/ -q` from the root. `python` is
     not on PATH — use `python3`.
   - `make check` = `check-node` + `check-py`; `make lint` / `make fmt-check` /
     `make lint-fix` / `make fmt`; `make precommit` runs the full gate.

4. **Implement the safe, high-leverage fixes now.** Knowledge capture, new tests
   that pin a corner case, scoped `Makefile` targets, deduplication, and lint/CI
   gates are usually safe to just do. Promote standards up the ratchet:
   prose in `docs/` → a test → a lint/type rule → a CI-blocking check. Keep any
   `CLAUDE.md`/`.jules/*.md` edits small and stable (every edit busts the prompt
   cache for future sessions).

5. **Ask before anything heavy or hard to reverse** — new dependencies, browser or
   tool installs, CI workflow changes, file moves, anything outward-facing (Anki
   addon publishing, R2 uploads, graph pushes). Present the trade-off and let the
   user choose; don't do it unilaterally.

6. **Verify and report.** Run the relevant `make` checks (at minimum `make check-py`
   for Python changes, `make check` for cross-cutting ones), keep tests and lint
   green, and summarize what you changed and exactly how it pays off next time.
   Do not commit unless explicitly asked.

Guiding test: _a correction given today should be impossible to need next month_ —
because it now lives in the repo (a doc, a test, a Makefile target, a gate), not in
this conversation.
