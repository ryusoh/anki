# Speeding up `make precommit-fix` (SKIP=1 and YOLO=1)

| Field    | Value                                                                                                                                                                                |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Status   | Implemented 2026-07-13 (§7.1-7.6; §7.7 skipped, below threshold — see §10). `make precommit SKIP=1` measured 98.65s post-implementation vs the 337s baseline. §7.8 (micro) not done. |
| Audience | Implementing agent (smaller model). Read `docs/delegation-specs.md` rules first.                                                                                                     |
| Scope    | `Makefile` orchestration only — no addon source, no test, no tool-config changes.                                                                                                    |
| Baseline | Measured 2026-07-13 on the primary machine (8 cores, GNU Make 3.81, warm caches).                                                                                                    |

## 1. Question

`make precommit-fix SKIP=1` and `make precommit-fix YOLO=1` run every step
serially. Which steps have real ordering dependencies, which can run in
parallel or be reordered (e.g. commit+push as soon as the tree is
commit-ready instead of at the very end), and what is the concrete plan to
cut wall-clock time for both modes?

## 2. Answer (TL;DR)

Measured baseline: `SKIP=1` ≈ **5 min 37 s** serial; `YOLO=1` adds fetch,
graph exports, R2 sync (**~3–5 min of pure network, per
`docs/r2-sync-guide.md`**), uploads and push on top, for roughly **10–13
min**. Almost all of it is parallelizable or overlappable:

1. The verify gate (`fmt-check lint quality-py check`, 291 s serial) is
   entirely **read-only** → run it under `make -j` (§7.1). The gate's
   internal giant, `check-py` (155 s), is a serial loop over 22 independent
   pytest suites → fan the suites out with per-suite coverage data files +
   `coverage combine` (§7.2).
2. In YOLO mode the R2 sync upload (the single longest step) only depends on
   `fetch-and-stage-r2`, **not** on the gate → start it in the background
   right after staging and `wait` for it at the end (§7.4).
3. Commit+push only needs: fetch outputs + fixer outputs + green gate +
   green security scan — graph exports and the R2 upload's own file output
   are gitignored/network-only, so commit and push immediately after the
   gate, in parallel with the uploads (§7.5). **Correction, 2026-07-13**:
   the R2 upload has one tracked side effect (`data/cloudflare/hash_map.json`)
   the original version of this section missed — see §4's "Key verified
   fact" and §7.5's follow-up-commit note.
4. `install` runs `npm ci` (15.5 s) on **every** invocation even when
   `package-lock.json` is untouched → stamp-file it (§7.3).
5. Cache flags for the JS tools (`prettier --cache`, `eslint --cache`,
   `stylelint --cache`) cut the fixer+format-check passes on warm runs
   (§7.6).

Projected result: `SKIP=1` ≈ **1.5–2 min** (~3×); `YOLO=1` ≈ **4–6 min**,
dominated by the un-shrinkable R2 sync, with the git push landing several
minutes earlier than today (~2×).

## 3. Measured baseline

Method: each target run via `time make <target>` on a clean, CI-green tree
(so fixers were no-ops), sequentially, 1 run each, 2026-07-13. Raw log:
session scratchpad `timings.log`. Warm caches (`.mypy_cache`, npm cache)
— cold-start numbers will be worse; see §10.

| Step (Makefile target)                             | Wall time    | Notes                                                                                                       |
| -------------------------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------- |
| `install` (pip no-op + `npm ci`)                   | 16.3 s       | `npm ci` = 15.5 s, runs unconditionally every invocation                                                    |
| `fmt` (Prettier write)                             | 8.1 s        | fixer                                                                                                       |
| `lint-fix` (ESLint/Stylelint/markdownlint `--fix`) | 10.2 s       | fixer; recursively invokes `$(MAKE) lint-md-fix`                                                            |
| `fmt-py` (black + ruff --fix)                      | 1.4 s        | fixer                                                                                                       |
| `fmt-check`                                        | 7.2 s        | gate                                                                                                        |
| `lint-js`                                          | 3.5 s        | gate                                                                                                        |
| `lint-css`                                         | 3.3 s        | gate                                                                                                        |
| `lint-md`                                          | 4.1 s        | gate                                                                                                        |
| `lint-py` (ruff)                                   | 0.7 s        | gate                                                                                                        |
| `fmt-py-check` (black --check)                     | 1.6 s        | gate                                                                                                        |
| `typecheck` (mypy)                                 | 2.3 s        | gate; **warm** `.mypy_cache`                                                                                |
| `security-py` (bandit)                             | 14.6 s       | gate; slowest quality-py tool                                                                               |
| `check-node`                                       | 98.8 s       | gate; node runner **then** jest, serial inside one recipe                                                   |
| `check-py`                                         | 155.4 s      | gate; 22 suites serial (116 s CPU → parallelizes well)                                                      |
| `data/anki/security_check.py`                      | 7.2 s        | read-only scan, runs unconditionally in `precommit-fix`                                                     |
| Makefile parse overhead                            | 0.74 s       | per `make` invocation (five `$(shell git ls-files …)` lists); YOLO does ~6 recursive `$(MAKE)` calls ≈ +4 s |
| `fetch-and-stage-r2`                               | not measured | mutates tracked files — not safely re-runnable for timing (§10)                                             |
| R2 sync upload                                     | ~3–5 min     | documented: "List: ~3–5 minutes" for 161K objects, `docs/r2-sync-guide.md` §Performance                     |
| `graph-local`, `graph-push`                        | not measured | §10                                                                                                         |

Serial totals: verify gate = 291.5 s; `SKIP=1` end-to-end ≈ 337 s.

## 4. Step inventory — what each step reads and writes

This is the evidence base for every reordering claim. Anchors are construct
names in `Makefile` (line numbers are hints only — re-verify before editing;
if drifted, locate by name).

| Step                                                                         | Recipe anchor                             | Tracked files                                                                                                                        | Gitignored files                                                                                                                                                                                                                                                | Network                                                                    |
| ---------------------------------------------------------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| `install`                                                                    | `install:` (Makefile:88)                  | —                                                                                                                                    | `node_modules/`, `.venv`                                                                                                                                                                                                                                        | npm/pip registries                                                         |
| `fetch-and-stage-r2`                                                         | `fetch-and-stage-r2:` (Makefile:107)      | **writes** `data/anki/*.json(.gz)`, `data/anki/reviews/*` (tracked — verified via `git ls-files data/anki`)                          | writes R2 staging dir (gitignored; enforced by `check_r2_staging_directory` in `data/anki/security_check.py`)                                                                                                                                                   | reads local Anki SQLite only (`docs/fetch-data-lag.md`)                    |
| `fmt` / `lint-fix` / `fmt-py`                                                | `fmt:`, `lint-fix:`, `fmt-py:`            | **write** JS/CSS/MD/JSON/HTML resp. `*.py`                                                                                           | —                                                                                                                                                                                                                                                               | —                                                                          |
| Verify gate (`VERIFY_GATE := fmt-check lint quality-py check`, Makefile:358) | each sub-target                           | **read-only**                                                                                                                        | `check-py` writes `.coverage*` (gitignored); `check-node` writes a mktemp covdir                                                                                                                                                                                | —                                                                          |
| `security_check.py`                                                          | `precommit-fix:` recipe body              | read-only                                                                                                                            | read-only                                                                                                                                                                                                                                                       | —                                                                          |
| `graph-local`                                                                | `graph-local:` (Makefile:159)             | —                                                                                                                                    | writes `graph/*.json` — **all gitignored** (`graph/.gitignore` line 1: `*.json`; only non-JSON exception is tracked `.incremental_config.json`… which is tracked because gitignore lists `*.json` yet the file was force-added; verify with `git check-ignore`) | reads Anki DB                                                              |
| `fetch-r2-skip-fetch` (R2 sync upload)                                       | `fetch-r2-skip-fetch:` (Makefile:112)     | **writes** `data/cloudflare/hash_map.json` (tracked — `save_hash_map()` in `data/anki/upload-to-r2`, only after a successful upload) | reads staging dir                                                                                                                                                                                                                                               | **~3–5 min** R2 list+upload (observed 15-20+ min for a full `--sync` pass) |
| `graph-push` = `graph-public` + upload                                       | `graph-push: graph-public` (Makefile:155) | —                                                                                                                                    | writes `graph/*_public.json` (gitignored, see `OUTPUT_FILE` in `graph/export_history.py`)                                                                                                                                                                       | uploads via `graph/upload_public.py`                                       |
| commit+push                                                                  | end of `precommit-fix:` recipe            | `git add -A && git commit && git push`                                                                                               | —                                                                                                                                                                                                                                                               | git remote                                                                 |

Key verified fact, corrected 2026-07-13 (was wrong in the original version
of this doc — see below): **`git add -A` picks up nothing from `graph-local`
or `graph-push`** — their file outputs are all gitignored and their other
effects are network-only. `fetch-r2-skip-fetch` is the **one exception**: it
mutates `data/cloudflare/hash_map.json`, a tracked file, via
`save_hash_map()` in `data/anki/upload-to-r2` — but only _after_ the network
upload completes, which in YOLO mode is backgrounded and can finish well
after the main commit already ran (§7.4/§7.5). Losing this file (not
tracking it at all) is not a safe fix: `upload-to-r2`'s `--upload-only` path
decides what to upload purely from the local hash map (`old_hash_map.get(guid)
is None` → upload) with no fallback check against what's actually already in
the R2 bucket, so a missing/empty hash map silently behaves like `--full`
and re-uploads everything — see `docs/incremental-staging.md`. The actual
fix implemented: a small follow-up commit for just `hash_map.json`, fired
right after the R2 background job's `wait` succeeds, separate from the main
commit (see the `precommit-fix` recipe).

## 5. Hard ordering constraints (the real DAG)

Constraints that MUST be preserved, with reasons:

1. **Fixers before the verify gate.** The gate checks the fixed state;
   that's the whole fix-then-verify contract (comment above `precommit-fix:`).
2. **`fmt` (Prettier) and `lint-fix` (ESLint `--fix`) must not run
   concurrently with each other** — both rewrite the same `*.js` files
   (Prettier's `PRETTIER_FILES` includes `JS_FILES`; ESLint runs `eslint .`).
   Same for Stylelint/markdownlint vs Prettier on CSS/MD. Keep the JS/CSS/MD
   fixers as one serial chain. `fmt-py` touches only `*.py` → MAY run in
   parallel with that chain.
3. **`fetch-and-stage-r2` before commit** (it writes tracked data files) and
   **before the R2 upload** (upload reads the staging dir). It does NOT
   block the fixers: Prettier/ESLint file lists exclude `data/`
   (`JSON_FILES` filter, Makefile:26), so no shared files.
4. **`security_check.py` must pass before commit** — it is the private-data
   guard (`docs/security-protocol.md`). It is read-only, so it MAY run
   concurrently with the gate, but its exit code MUST gate the commit.
5. **Commit only after the full verify gate is green** — a green
   `precommit-fix` must keep meaning "CI will be green" (`VERIFY_GATE` is
   shared with `precommit`/CI; see §8).
6. **`graph-public` before `graph/upload_public.py`** (the upload reads the
   `*_public.json` it writes) — already encoded as `graph-push: graph-public`.
7. **Everything that mutates tracked files before `security_check.py`'s
   scan** (it scans final tree state): fetch + fixers first.
8. Within `check-py`, suites MUST remain **separate pytest invocations**
   (per-addon `sys.path` bootstrap — comment above `PY_TEST_SUITES`,
   Makefile:260). Parallelism must come from fanning out invocations, never
   from one combined run.

Explicit non-constraints (verified above): gate ↛ R2 upload, gate ↛ graph
exports, graph-local ↛ commit, R2 upload ↛ commit.

## 6. Target execution schedule

`GNU Make 3.81` (Apple's bundled make — verified `make --version`) supports
`-j` but NOT `.WAIT`, grouped targets, or `--output-sync` (all 4.x). The
design therefore uses **two-phase recursive make**: run fixers serially,
then `$(MAKE) -j$(JOBS) <read-only targets>` for the parallel phase. Do NOT
add a bare `MAKEFLAGS += -j` at top level — left-to-right prerequisite
ordering of `precommit-fix` would silently break.

`SKIP=1` schedule (time →):

```text
install(stamped, ~0s)
fixers: [fmt → lint-fix] ∥ [fmt-py]                 ~10–18 s
$(MAKE) -j8: fmt-check lint-js lint-css lint-md
             lint-py fmt-py-check typecheck security-py
             check-node-par check-py-par security-scan   ~60–100 s (bounded by check-py-par)
[commit+push only if MSG=…]
```

`YOLO=1` schedule:

```text
install(stamped) → fetch-and-stage-r2               (writes tracked data + staging)
  ├─ background: R2 sync upload  ──────────────── ~3–5 min ─┐
  ├─ background: graph-local + graph-public → graph-push ───┤
  └─ foreground: fixers → $(MAKE) -j8 gate + security-scan  │
       └─ commit + push  (gate+scan green; ~min 2–3) ───────┤
wait for background jobs; print their logs; fail if any failed
```

Critical path becomes `fetch + max(R2 sync, fixers+gate) + wait` instead of
the sum of everything.

## 7. Implementation plan (ordered, independently shippable)

Each step: change → expected saving → verify command. Ship and commit them
one at a time; each MUST leave `make precommit SKIP=1` green.

### 7.1 Parallel verify gate (biggest structural win)

- Add `JOBS ?= $(shell sysctl -n hw.ncpu 2>/dev/null || echo 4)`.
- Add a phony `verify` target whose recipe is
  `$(MAKE) -j$(JOBS) $(VERIFY_GATE)`, and use it from both `precommit` and
  `precommit-fix` in place of the inline `$(VERIFY_GATE)` prerequisite list.
  This keeps the CI-parity property: both paths still execute exactly
  `$(VERIFY_GATE)`.
- All gate members are read-only (§4); the only shared-resource hazards are
  `.coverage` (only `check-py` touches it) and CPU oversubscription
  (acceptable).
- Saving: gate 291 s → ~max(check-py, check-node) once 7.2/7.7 also land;
  even alone (check-py still 155 s serial) the other 136 s of gate work
  hides inside it → gate ≈ 160 s.
- Verify: `time make verify` twice (warm), compare against §3; then
  `make precommit SKIP=1` still green.

### 7.2 Parallelize `check-py` across suites

Replace the serial `for suite in $(PY_TEST_SUITES)` loop with a fan-out.
Preferred shape (static pattern rule keeps make as the scheduler and
propagates failures). NOTE: recipe lines in every `make` snippet in this doc
are indented with spaces (repo markdownlint forbids hard tabs in docs) — in
the real Makefile they MUST be hard tabs or make errors with "missing
separator":

```make
PY_COV_DIR := coverage/py-data
PY_SUITE_TARGETS := $(addprefix pysuite/,$(PY_TEST_SUITES))
.PHONY: $(PY_SUITE_TARGETS)
$(PY_SUITE_TARGETS): pysuite/%:
    @COVERAGE_FILE=$(PY_COV_DIR)/.coverage.$(subst /,_,$*) \
      $(PYTHON) -m pytest -q --cov --cov-report= "$*"

check-py:
    @mkdir -p $(PY_COV_DIR); rm -f $(PY_COV_DIR)/.coverage.*
    @$(MAKE) -j$(JOBS) $(PY_SUITE_TARGETS)
    @$(PYTHON) -m coverage combine $(PY_COV_DIR)
    @$(PYTHON) -m coverage report -m
```

- `COVERAGE_FILE` is the documented env var for the data-file path
  (<https://coverage.readthedocs.io/en/latest/cmd.html#data-file>), and
  `coverage combine <dir>` merges `.coverage.*` files from a directory
  (<https://coverage.readthedocs.io/en/latest/cmd.html#cmd-combine>).
  `--cov-append` is then obsolete and MUST be dropped (separate files).
  First implementation action: confirm pytest-cov honors `COVERAGE_FILE`
  with a 2-suite smoke run before converting the whole loop (§10 item 3).
- Keep invoking coverage as `$(PYTHON) -m coverage` — the repo-root
  `coverage/` directory shadows the bare command (CLAUDE.md gotcha).
- Do NOT reach for pytest-xdist here — cross-suite fan-out already saturates
  8 cores with 22 suites, without touching test code.
- Interleaved suite output is acceptable for v1; if it bothers, redirect each
  suite to `$(PY_COV_DIR)/$*.log` and `cat` on failure.
- Saving: 155 s wall / 116 s CPU → bounded by the slowest single suite;
  expect **~30–60 s**.
- Verify: `time make check-py`; total test count and coverage percentage in
  the report MUST match the serial run's; then run it twice to check for
  flaky parallel interactions.

### 7.3 Stamp-file `install`

```make
.make/npm-ci.stamp: package-lock.json | .venv
    @npm ci
    @mkdir -p .make && touch $@
```

plus an analogous `.make/pip.stamp: requirements.txt`. `install` keeps its
current behavior; `precommit-fix` depends on the stamps instead. Add
`FORCE_INSTALL=1` escape hatch (delete stamps first). Reason this is safe:
the CLAUDE.md drift gotcha is about `package.json` changing without `npm ci`
rerunning — the stamp reruns `npm ci` exactly when `package-lock.json`
changes, which is the same trigger CI's cache uses. `.make/` MUST be added
to `.gitignore`.

- Saving: 16.3 s → ~0 s on every run where the lockfile is unchanged (the
  overwhelming majority).
- Verify: run twice; second run must skip `npm ci`. Then `touch
package-lock.json` and confirm it reruns.

### 7.4 YOLO: background the network I/O

In the `precommit-fix` recipe (YOLO path only), immediately after
`fetch-and-stage-r2` completes:

```sh
python3 data/anki/upload-to-r2 --upload-only --sync --verbose \
  > .make/r2-upload.log 2>&1 & R2_PID=$!
( $(MAKE) graph-local && $(MAKE) graph-push ) \
  > .make/graph.log 2>&1 & GRAPH_PID=$!
```

then proceed with fixers + gate, and at the end
`wait $R2_PID; wait $GRAPH_PID`, `cat` both logs, and exit non-zero if
either failed. (Concurrent readers of the Anki SQLite file are fine — both
scripts copy/read only; `docs/fetch-data-lag.md` documents the read path.)

- **Policy note (needs user sign-off, see §9):** this uploads to R2 even if
  the gate later fails. The data uploaded is identical either way (it
  depends only on the fetch), so the failure mode is "synced data for a
  commit that didn't happen" — same category as answering `y` to today's
  prompt and then not committing. If unacceptable, guard with
  `EARLY_UPLOAD=0` to restore the serial order.
- Saving: the entire R2 sync (~3–5 min, observed 15-20+ min in practice) and
  graph exports disappear from the critical path; YOLO total ≈ max(R2 sync,
  gate) + fetch + push.
- Verify: full `make precommit-fix YOLO=1` run; confirm both logs are
  printed, exit code reflects a forced upload failure (test by temporarily
  breaking the R2 credentials path). **Correction, 2026-07-13**: `git
status` is NOT necessarily clean right after — see the follow-up-commit
  note under §7.5 below; it converges once that fires, not immediately.

### 7.5 YOLO: commit and push as soon as the tree is commit-ready

Move the existing commit block (anchor: `📝 Committing:` in the
`precommit-fix` recipe) to run right after gate + `security_check.py`
succeed — i.e. **before** the `wait` from §7.4, not after the uploads.
`git push` (network) then overlaps the R2 upload.

**Correction, 2026-07-13 — the "nothing tracked" justification was wrong for
one file.** `graph-local`/`graph-push` really do write only gitignored
output, but the R2 upload's `save_hash_map()` call (in
`data/anki/upload-to-r2`, after a successful upload) mutates
`data/cloudflare/hash_map.json`, which **is** tracked. Since that upload is
now backgrounded and can finish after the main commit, its hash-map update
can miss the main commit entirely. Considered and rejected: untracking
`hash_map.json` (simplest, but `upload-to-r2 --upload-only` has no fallback
check against R2's actual state — a missing/empty hash map makes it
silently re-upload everything, see `docs/incremental-staging.md`); keeping
the R2 upload synchronous before commit (correct, but it's the single
slowest step — 15-20+ min observed — so this would defeat most of §7.4's
point). Implemented instead: right after the R2 background job's `wait`
succeeds, check `git diff --quiet -- data/cloudflare/hash_map.json`, and if
it changed, fire one small separate `git add`/`commit`/`push` for just that
file (message: `chore: update R2 hash map after sync`), unconditionally —
not gated on `GATE_OK`/`SEC_OK`, since the hash map's correctness is
independent of code quality, and not re-run through `security_check.py`,
since the file structurally cannot contain note content (GUID→SHA256 only).
If the process is killed before this fires (e.g. the terminal closes during
the still-running R2 sync), nothing is lost beyond that one commit being
deferred: `save_hash_map()` already wrote the correct file to disk
regardless of git, and the _next_ `precommit-fix` run's main `git add -A`
will pick up the stale-but-uncommitted file anyway.

- Saving: the push lands ~3–5 min earlier; total wall time drops by
  whatever the uploads no longer serialize (order of minutes).
- Verify: run with `MSG='test: …'` on a scratch branch first; confirm the
  commit contains fetch+fixer output only and never `graph/*.json`.

### 7.6 JS tool caches (cheap, independent)

- `fmt`/`fmt-check`: add `--cache` to the Prettier invocations (supported
  since Prettier 2.7: <https://prettier.io/docs/cli#--cache>; installed
  version 3.9.5, verified via `npx prettier --version`).
- `lint-js`/`lint-fix`: add `--cache --cache-location .make/eslintcache`
  (<https://eslint.org/docs/latest/use/command-line-interface#caching>).
- `lint-css`: add `--cache` (Stylelint 17,
  <https://stylelint.io/user-guide/options#cache>).
- CI is unaffected (fresh runner, cold cache = current behavior).
- **Related finding:** `prettier` and `markdownlint-cli` are NOT in
  `package.json` — `npx` resolves them from its own cache (verified:
  `node_modules/.bin` lacks both). They SHOULD be pinned as devDependencies
  (also makes `--cache` behavior version-stable), but that changes
  `package-lock.json` — flag it in the PR, don't slip it in silently.
- Saving: ~10–15 s warm across `fmt`, `lint-fix`, `fmt-check`, `lint-js`,
  `lint-css`.
- Verify: second consecutive `make fmt-check` drops from 7.2 s to ≲2 s.

### 7.7 Split `check-node` into two parallel targets

The recipe runs the node:test runner (with V8 coverage) and then jest
serially inside one shell. Split into `check-node-runner` and
`check-node-jest` phony targets so 7.1's `-j` runs them concurrently; keep
`check-node: check-node-runner check-node-jest` for compatibility. First
measure the split (unknown; §10) — if jest is ≥30 s this is worth ~30–40 s;
if it's ~10 s, skip this step.

- Verify: `time make -j2 check-node-runner check-node-jest` vs `time make
check-node`; identical test counts.

### 7.8 Micro (do last, or not at all)

- `CHECK_TOOL_VERSION` + the preceding availability check spawn the tool
  twice per gate target (~0.3–0.5 s each); merge into one spawn.
- The five `$(shell git ls-files …)` list pipelines cost ~0.74 s per make
  invocation and re-run in every recursive `$(MAKE)`; converting `:=` to
  lazy `=` helps only single-use variables (3.81 re-expands `=` per use).
  Reducing recursive `$(MAKE)` calls (e.g. inlining `lint-md-fix` into
  `lint-fix`) is the simpler ~2–4 s win in YOLO mode.

## 8. Invariants — DO-NOT list (reasons attached)

- **DO NOT let `precommit` and `precommit-fix` verify different things.**
  Both must keep referencing the single `VERIFY_GATE` variable — the
  Makefile comment ("single source of truth… can never silently diverge")
  is the contract CI relies on (`.github/workflows/ci.yml` runs
  `make precommit SKIP=1`).
- **DO NOT commit before both the gate and `security_check.py` pass** — the
  scan is the last line of defense against private Anki data reaching
  GitHub (`docs/security-protocol.md`).
- **DO NOT run Prettier concurrently with any of the ESLint/Stylelint/
  markdownlint fixers** — overlapping writers on the same files; a lost
  write surfaces later as a confusing `fmt-check` failure.
- **DO NOT merge the pytest suites into one invocation or share one
  `.coverage` file between concurrent suites** — collection breaks
  (per-addon `sys.path`) resp. data-file corruption; use per-suite
  `COVERAGE_FILE` + `combine`.
- **DO NOT set a global `MAKEFLAGS += -j`** — `precommit-fix`'s
  prerequisite list is order-dependent (fixers before gate) and make 3.81
  has no `.WAIT`; parallelism must stay inside the explicit
  `$(MAKE) -j$(JOBS)` sub-invocations.
- **DO NOT invoke bare `coverage`** — shadowed by the repo-root `coverage/`
  directory (CLAUDE.md).
- **DO NOT time or test `fetch-and-stage-r2` casually** — it rewrites
  tracked data files from the live Anki DB; a stale WAL state can make the
  diff misleading (`docs/fetch-data-lag.md`).

## 9. Acceptance criteria & predicted diff scope

- [x] Diff touches ONLY: `Makefile`, `.gitignore` (`.make/` entry),
      `docs/README.md` (index line), this doc's Status row. Zero diff in any
      addon directory, `tests/`, `tools/`, `.github/`. Confirmed with
      `git diff --stat` after each commit. The pinning side-quest in §7.6
      (prettier/markdownlint-cli as devDependencies) was NOT done — flagged
      only, per the doc's own "don't slip it in silently" note.
- [x] `make precommit SKIP=1` green after every step, and at final HEAD
      (98.65 s, exit 0).
- [x] `make check-py` parallel run reports the same test count (978 across
      22 suites) and coverage (5410/778/2132/184, 84%) as the serial
      baseline; reproduced across 2 consecutive runs (no flakiness); a
      deliberately-injected failing test correctly failed the target with
      all other suites still completing and the report still printing.
- [x] `time make precommit SKIP=1` (the CI-mirroring, no-fixer path)
      98.65 s ≤ 2.5 min warm (baseline 5 min 37 s). `precommit-fix SKIP=1`
      itself ran 172 s in one measurement, but that run's `npm ci` had real
      work to do (lockfile touched during §7.3 testing) and shared the
      machine with a concurrent, unrelated session's own test runs — not a
      clean warm-baseline comparison; the 98.65 s number is the reliable one.
- [x] §7.4/§7.5 background+wait mechanism validated in isolation (scratch
      Makefile: two backgrounded jobs, one deliberately failing, run
      concurrently with foreground work; confirmed wall time ≈ max not sum,
      and exit codes propagate through `wait $PID`) and the real gate-success
      vs gate-failure control flow validated via `make precommit-fix SKIP=1`
      (security-check/commit correctly run only on gate success; correctly
      skipped, with "❌ Pre-commit checks failed" and a non-zero exit, on a
      forced gate failure). **NOT** validated with a live `YOLO=1` run
      against real R2 credentials/git remote — that would itself be the
      real side-effecting action the design discusses, not a safe thing to
      trigger as a verification step. Whoever first runs `YOLO=1` for real
      should watch for: R2/graph upload logs printing correctly on `wait`,
      and the commit landing before those logs print.
- [x] User sign-off obtained via AskUserQuestion before implementing:
      (a) §7.4 uploads may complete even when the gate fails — approved;
      (b) §7.5 push happens before R2/graph uploads finish — approved.
- [x] (Unplanned, real-world) A concurrent session in the same working
      directory ran `make precommit-fix YOLO=1` for its own unrelated fix
      partway through this implementation and its `git add -A` swept up the
      then-uncommitted §7.4/§7.5 Makefile changes into its own commit
      (`e3800278`, message unrelated to this work), which was pushed to
      `origin/main` before this implementing session could commit it with
      an accurate message. Content was verified correct before and after;
      this is noted here rather than fixed by rewriting shared history. It
      is also, incidentally, a real (if accidental) live-fire confirmation
      that a `YOLO=1` run using the new code path completed and pushed
      successfully.

## 10. Open questions / what was not measured

1. **`fetch-and-stage-r2`, `graph-local`, `graph-push` durations** — not
   safely re-runnable for timing (tracked-file writes / real uploads).
   Implementer: capture timestamps from one real YOLO run's log before and
   after §7.4 to quantify the actual win.
2. **Slowest single pytest suite** bounds §7.2's ceiling — measure with the
   per-suite fan-out's logs; if one suite is ≫60 s, consider pytest-xdist
   for that suite only (respecting the ProcessPoolExecutor mock gotcha in
   `docs/creating-an-addon.md`).
3. **pytest-cov + `COVERAGE_FILE`** interaction assumed from coverage.py
   docs; smoke-test with 2 suites before converting (explicit first action
   in §7.2).
4. **check-node internal split** (node runner vs jest) — measured 2026-07-13:
   node:test runner ~51 s, jest ~1.5–5 s (jest was much slower — 50–98 s — in
   earlier measurements, but that was the jsdom-29/Node-22 ESM incompatibility
   breaking `review_heatmap/tests/*.test.js`, since fixed; not a splitting
   issue). Below the doc's own "≥30 s" bar for §7.7 — **skipped**: node:test
   alone already dominates check-node's wall time, so splitting the two into
   parallel sub-targets would save only the few seconds jest overlaps, not
   worth the added target/complexity.
5. **Cold-cache numbers**: mypy was warm (2.3 s); a cold `.mypy_cache` run
   will make `typecheck` a temporary critical-path item but changes no
   ordering decision.
6. Timings are single-run on one machine; treat ±20% as noise.
