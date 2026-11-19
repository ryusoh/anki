---
description: Test-driven development. Use when the user wants to build features or fix bugs test-first, mentions "red-green-refactor", or wants integration tests.
---

# Test-Driven Development

Goal: a red → green loop that leaves behind tests worth keeping — tests that
read like a specification and survive refactors. Read
`docs/creating-an-addon.md` (and `docs/js-testing.md` for JS work) first so
test names and interfaces match this repo's conventions.

## Where TDD pays off here

Strongest on pure-Python addon logic — parsers, text transforms
(`auto_wiktionary/`, `strip_html_tags/`), and the graph pipeline (`graph/`) —
deterministic input → output with clean seams. Corner-case tests live next to
each addon in `<addon>/tests/` (e.g. `auto_wiktionary/tests/` pins Wiktionary
redirect cases).

Where the code meets real Anki (hook wiring, Qt UI, WebView injection), root
`conftest.py` mocks `aqt`/`anki`, and browser scripts use source-level
regression tests (`docs/js-testing.md`) — a green test proves the logic against
the mock, and real-Anki behavior still needs an Anki launch to verify.

## Test runners

- Run from the repo root (root `conftest.py` provides the `aqt`/`anki` mocks).
- Scoped Python loop: `make test-py SUITE=<addon>/tests` (or
  `python3 -m pytest <addon>/tests/ -q`).
- Scoped JS loop: only root `tests/` (node runner) and `review_heatmap/tests/`
  (jest) execute — run one file via
  `node --experimental-vm-modules --no-warnings tests/<file>.test.mjs`.
- Full verification: `make check`, and `make precommit SKIP=1` for CI parity.
  Re-verify under `.venv/bin/python3` (what `make` uses).
- Patch `ProcessPoolExecutor` to `ThreadPoolExecutor` in tests (spawned
  children re-import modules and drop mocks).

## Good tests

- Assert observable output through public interfaces — the transformed note
  text, exported graph JSON shape, or parsed field.
- Take expected values from an independent source of truth (a worked example,
  known-good literal, or captured real payload) so the test can disagree with
  the code.
- Mock at the system boundary (root `conftest.py` already mocks `aqt`/`anki`);
  prefer real fixtures (captured Wiktionary response, sample export) for
  collaborators the repo owns.

## Seams

A seam is the public boundary you test at. Before writing tests, propose the
seams under test and agree them with the user ("What's the public interface,
and which seams matter?") so effort lands on critical paths.

## The loop

Work in vertical slices: one seam → one failing test → the minimal code that
passes it → repeat. Each slice is a tracer bullet; writing all tests up front
verifies imagined behavior. Refactoring happens in review after the loop.

Smells to correct: tests that break on a refactor with unchanged behavior
(coupled to internals), and assertions that recompute the expected value the
way the code does (tautological).

## Resume protocol

After an interruption or compaction: `git status --short`,
`git log -n 3 --oneline`, and the scoped test run show the real state. State
the current slice, its failing assertion, and the minimal implementation target
before editing.
