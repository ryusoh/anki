---
name: tdd
description: Test-driven development. Use when the user wants to build features or fix bugs test-first, mentions "red-green-refactor", or wants integration tests.
---

# Test-Driven Development

TDD is the red → green loop. This skill is the reference that makes that loop
produce tests worth keeping: what a good test is, where tests go, the
anti-patterns, and the rules of the loop. Consult it before and during the loop.

Before exploring, read `docs/creating-an-addon.md` (layout, hook/test patterns)
and, for JS work, `docs/js-testing.md`, so test names and interface vocabulary
match this repo's conventions.

## Where this fits in this repo — and where it does NOT

TDD earns its keep on **pure-Python addon logic** — parsers and text transforms
(`auto_wiktionary/`, `strip_html_tags/`), the graph data pipeline (`graph/`) —
deterministic input→output code with clean seams. The house pattern: corner-case
tests live next to each addon in `<addon>/tests/` (e.g. `auto_wiktionary/tests/`
pins Wiktionary redirect cases) — add a failing test there first, then fix.

It is **weak where the code meets real Anki.** The root `conftest.py` mocks
`aqt`/`anki`, so a green test proves your logic against the mock, not against
Anki itself — hook wiring, Qt UI, and webview injection need a launch of real
Anki to verify. Likewise, browser-side scripts are pinned with source-level
regression tests (`docs/js-testing.md`): those prove the source text, not
runtime behavior. A passing test is necessary, not sufficient, there.

## Test runners

- **Always run from the repo ROOT** — `pytest` inside an addon subdir fails
  with `ModuleNotFoundError` (the root `conftest.py` provides the mocks).
- Scoped Python, tight loop: `python3 -m pytest <addon>/tests/ -q` (or
  `make test-py SUITE=<addon>/tests`).
- Scoped JS: only root `tests/` (node runner) and `review_heatmap/tests/`
  (jest) are executed — a `*.test.js` anywhere else silently never runs. One
  file: `node --experimental-vm-modules --no-warnings tests/<file>.test.mjs`.
- Full suite before declaring done: `make check`; `make precommit SKIP=1`
  matches CI. `make` runs `.venv/bin/python3`, not your shell's `python3` —
  re-verify with `.venv/bin/python3` before trusting green.
- Never spawn a real `ProcessPoolExecutor` in a test — spawn children re-import
  the module and drop your mocks; patch it to `ThreadPoolExecutor`.

## What a good test is

Tests verify behavior through public interfaces, not implementation details. Code
can change entirely; tests shouldn't. A good test reads like a specification —
"redirect page resolves to its target entry" — and survives refactors. In
practice here:

- **Assert on observable output**, not internal structure: the transformed note
  text, the exported graph JSON shape, the parsed field — not a private helper.
- **Expected values come from an independent source of truth** — a worked
  example, a known-good literal, a captured real payload — never recomputed the
  way the code computes them.
- **Mock at the boundary, not the internals.** Prefer real fixtures (a captured
  Wiktionary response, a small sample export) over mocking a collaborator you
  own. The `aqt`/`anki` mock is the one boundary already mocked for you.

## Seams — where tests go

A **seam** is the public boundary you test at: where you observe behavior without
reaching inside. **Test only at pre-agreed seams.** Before writing any test, write
down the seams under test and confirm them with the user — you can't test
everything, and agreeing seams up front is how effort lands on critical paths and
complex logic. Ask: "What's the public interface, and which seams should we test?"

## Anti-patterns

- **Implementation-coupled** — mocks internal collaborators, tests private methods,
  or verifies through a side channel. Tell: breaks on refactor though behavior is
  unchanged.
- **Tautological** — the assertion recomputes the expected value the way the code
  does (`expect(add(a,b)).toBe(a+b)`), so it can never disagree with the code.
  This repo once carried a whole file of these (`graph/tests/test_glass_radius`,
  deleted): it asserted on its own inline constants and imported no source at all.
- **Horizontal slicing** — all tests first, then all implementation. Bulk tests
  verify _imagined_ behavior and go insensitive to real changes. Work in **vertical
  slices**: one test → one implementation → repeat, each a tracer bullet.

## Rules of the loop

- **Red before green.** Failing test first, then only enough code to pass it. No
  speculative features.
- **One slice at a time.** One seam, one test, one minimal implementation per cycle.
- **Refactoring is not part of the loop.** It belongs to review — run `/code-review`
  after the red → green cycle, not during it.
