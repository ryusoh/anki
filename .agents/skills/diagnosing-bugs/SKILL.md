---
name: diagnosing-bugs
description: Diagnosis loop for hard bugs and performance regressions. Use when the user says "diagnose"/"debug this", or reports something broken/throwing/failing/slow.
---

# Diagnosing Bugs

A discipline for hard bugs. Skip phases only when explicitly justified.

Before exploring, read the governing doc so you have a mental model before
touching code: `docs/creating-an-addon.md` (addon layout, hooks, test patterns),
`docs/js-testing.md` (which JS tests actually run), the graph docs
(`docs/anki-knowledge-graph-architecture.md`, `docs/graph-analysis-guide.md`),
or the data-pipeline docs (`docs/anki-data-fetch.md`, `docs/r2-sync-guide.md`).
Several of this repo's worst bugs are **silent wrong output, not an error**.

## This repo's silent-failure trap classes — suspect these first

These stay green or render wrong values with **no error**, so a naive loop
passes while the bug is live:

- **A test that never runs.** Only root `tests/` (node runner) and
  `review_heatmap/tests/` (jest) execute JS tests — a `*.test.js` anywhere else
  is dead weight that "passes" forever. Likewise `pytest` collects per-addon
  suites only from the repo root.
- **Green under one interpreter, red under the other.** `make` runs
  `.venv/bin/python3`; your shell runs Homebrew `python3` — different packages
  (e.g. `fa2_modified`). Re-run with `.venv/bin/python3` before debugging a
  "flaky" failure.
- **The mock isn't Anki.** Root `conftest.py` mocks `aqt`/`anki`, so hook
  signatures, Qt behavior, and webview quirks diverge silently — the suite
  cannot see a bug that only manifests in real Anki.
- **`ProcessPoolExecutor` in tests** — spawn children re-import modules and
  drop your mocks, so patched behavior silently reverts in the child. Patch it
  to `ThreadPoolExecutor`.
- **Bare `coverage`** resolves to the repo-root `coverage/` directory, not the
  tool — invoke `python3 -m coverage`.

## Phase 1 — Build a feedback loop

**This is the skill.** Everything else is mechanical. If you have a **tight**
pass/fail signal that goes red on _this_ bug, you will find the cause. If you
don't, no amount of staring at code will save you. Spend disproportionate effort
here. **Be aggressive. Be creative. Refuse to give up.**

### Ways to construct one — roughly in this order

1. **Scoped failing test** at the seam that reaches the bug — from the repo
   root: `python3 -m pytest <addon>/tests/ -q` for Python; for JS, one file via
   `node --experimental-vm-modules --no-warnings tests/<file>.test.mjs` or
   `npx jest review_heatmap/tests/<file>`.
2. **CLI / pipeline invocation** with a fixture input, diffing output against a
   known-good snapshot — the graph pipeline (`graph/export_data.py`,
   `graph/incremental_export.py`) against captured JSON.
3. **Real Anki launch** with the addon installed — the loop for hook, Qt UI,
   and webview bugs the mocked suite can't see.
4. **Replay a captured artifact** — save a real payload (a Wiktionary response,
   an exported graph JSON) to disk and replay it through the code path in
   isolation.
5. **Throwaway harness** — minimal subset that exercises the bug path in one call.
6. **Property / fuzz loop** — for "sometimes wrong output", run many random inputs.
7. **Differential loop** — same input through old vs new (or two configs), diff.

Build the right feedback loop, and the bug is 90% fixed.

### Tighten the loop

- **Faster** — scope the test to one file; skip unrelated init.
- **Sharper** — assert the specific symptom, not "didn't crash".
- **Deterministic** — pin time, seed RNG, isolate the filesystem, and run under
  the same interpreter `make` uses (`.venv/bin/python3`).

### When you genuinely cannot build a loop

Stop and say so. List what you tried. For bugs in real-Anki rendering or Qt
behavior the honest loop is often "the user looks at Anki" — ask them to look
rather than claiming a fix from a green mocked test. Do **not** proceed to
hypothesise without a loop.

### Completion criterion — a tight loop that goes red

Phase 1 is done when you can name **one command** you have **already run once**
(paste the invocation and output) that is: **red-capable** (drives the real bug
path, asserts the user's exact symptom), **deterministic**, **fast**, and
**agent-runnable**. If you catch yourself building a theory before this command
exists, **stop** — jumping to a hypothesis is the exact failure this prevents.

## Phase 2 — Reproduce + minimise

Run the loop, watch it go red. Confirm it's the **user's** symptom, not a nearby
one. Then shrink to the **smallest scenario that still goes red** — cut inputs,
callers, config, data one at a time, re-running after each cut. Done when every
remaining element is load-bearing. The minimal repro becomes the Phase 5 test.

## Phase 3 — Hypothesise

Generate **3–5 ranked, falsifiable hypotheses** before testing any. Each states a
prediction: "If X is the cause, changing Y makes the bug disappear." Show the list
to the user before testing — they often re-rank instantly. Don't block if AFK.

## Phase 4 — Instrument

Each probe maps to one Phase-3 prediction. **Change one variable at a time.**
Prefer a debugger/REPL over logs. **Tag every debug log** with a unique prefix
(`[DEBUG-a4f2]`) so cleanup is one grep. For perf regressions, **measure first**
(profiler, `time.perf_counter()`) — logs are usually the wrong tool.

## Phase 5 — Fix + regression test

Write the regression test **before the fix**, but only if a **correct seam**
exists — one that exercises the real bug pattern at the call site. If the only
seam is too shallow (or the bug lives behind the `aqt` mock and is untestable,
per the trap above), **that itself is the finding** — note it. Otherwise:
failing test → watch fail → fix → watch pass → re-run the Phase-1 loop on the
original scenario. For real-Anki behavior, have the user verify in Anki — a
green mocked test proves the logic, not the integration.

## Phase 6 — Cleanup + post-mortem

- [ ] Original repro no longer reproduces
- [ ] Regression test passes (or absence of seam documented)
- [ ] All `[DEBUG-...]` instrumentation removed (`grep` the prefix)
- [ ] Throwaway harnesses deleted
- [ ] The correct hypothesis stated in the commit / PR message
- [ ] `make precommit SKIP=1` (or a scoped `make test-py SUITE=...` + lint) is green

**Then ask: what would have prevented this bug?** If the answer is a durable repo
improvement — a knowledge doc, a `Makefile` target, a lint/CI gate, an AGENTS.md
line — hand off to `/retro` with the specifics, **after** the fix is in.
