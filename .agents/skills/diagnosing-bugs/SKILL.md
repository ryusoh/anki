---
name: diagnosing-bugs
description: Diagnosis loop for hard bugs and performance regressions. Use when the user says "diagnose"/"debug this", or reports something broken/throwing/failing/slow.
---

# Diagnosing Bugs

The goal is a confirmed root cause with a regression test, reached through a
feedback loop rather than code-staring. Start by reading the governing doc for
the area: `docs/creating-an-addon.md`, `docs/js-testing.md`,
`docs/anki-knowledge-graph-architecture.md`, `docs/graph-analysis-guide.md`,
`docs/anki-data-fetch.md`, or `docs/r2-sync-guide.md`. Many of this repo's
worst bugs are silent wrong output, not errors.

## Suspect the silent-failure classes first

- **A test that silently skips.** Only root `tests/` (node runner) and
  `review_heatmap/tests/` (jest) execute JS tests; a `*.test.js` elsewhere
  passes without running. `pytest` collects per-addon suites only from the repo
  root.
- **Interpreter mismatch.** `make` runs `.venv/bin/python3`; your shell runs
  Homebrew `python3` with different packages (e.g. `fa2_modified`). Re-run with
  `.venv/bin/python3` first.
- **The mock diverges from Anki.** Root `conftest.py` mocks `aqt`/`anki`, so
  hook signatures, Qt behavior, and WebView quirks can fail only in real Anki.
- **`ProcessPoolExecutor` in tests.** Spawned children re-import modules and
  drop mocks; patch it to `ThreadPoolExecutor`.
- **Bare `coverage`** resolves to the repo-root `coverage/` directory — invoke
  `python3 -m coverage`.

## Phase 1 — Build a red-capable loop (most of the effort goes here)

Done when you have run one command that drives the real bug path, asserts the
user's exact symptom, and is deterministic and fast. Candidates, roughly in
order:

1. Scoped failing test from repo root — `python3 -m pytest <addon>/tests/ -q`,
   `node --experimental-vm-modules --no-warnings tests/<file>.test.mjs`, or
   `npx jest review_heatmap/tests/<file>`.
2. CLI/pipeline invocation on a fixture diffed against a known-good snapshot
   (`graph/export_data.py`, `graph/incremental_export.py`).
3. Real Anki launch with the addon installed (for hook, Qt UI, and WebView
   bugs the mock hides).
4. Replay of a captured artifact (Wiktionary response, exported graph JSON).
5. Throwaway harness, property/fuzz loop, or old-vs-new differential run.

Pin time, seed RNG, isolate the filesystem, and run under `.venv/bin/python3`.
If no local loop is possible (common for real-Anki rendering or Qt bugs), say
so, list what you tried, and ask the user to inspect it in Anki.

## Phase 2 — Reproduce and minimise

Confirm the loop shows the user's symptom, then cut inputs, callers, config,
and data until every remaining element is load-bearing. The minimal repro
becomes the regression test.

## Phase 3 — Hypothesise

Write 3–5 ranked, falsifiable hypotheses ("if X, changing Y removes the bug")
and show them to the user before probing — they often re-rank instantly.
Continue without waiting if they're away.

## Phase 4 — Instrument

One probe per prediction, one variable at a time. Prefer a debugger/REPL over
logs; tag debug logs with a unique prefix (`[DEBUG-a4f2]`) so cleanup is one
grep. For perf, measure first (`time.perf_counter()`, profiler).

## Phase 5 — Fix with a regression test

At a seam that exercises the real bug pattern: failing test → fix → passing
test → re-run the Phase 1 loop. If the only seam is too shallow or lives behind
the `aqt` mock, record that as a finding and ask the user to verify in real
Anki.

## Phase 6 — Clean up and close

Original repro gone; regression test green (or missing seam documented);
`[DEBUG-` prefix grep empty; throwaway harnesses deleted; confirmed hypothesis
in the commit/PR message; `make precommit SKIP=1` (or scoped
`make test-py SUITE=...` + lint) green. If a durable repo change (doc, Makefile
target, gate) would have prevented the bug, hand it to `/retro` after the fix
lands.

## Resume protocol

After an interruption or compaction: `git status --short` and `git diff` to
find live probes, re-run the Phase 1 command to see current red/green, then
state the active phase, hypothesis under test, and next check before editing.
