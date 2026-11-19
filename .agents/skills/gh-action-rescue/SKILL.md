---
name: gh-action-rescue
description: Fully diagnose and repair a failed GitHub Actions workflow run, then automatically verify, commit, push, open and merge a PR, and trigger/verify a fresh run or deployment. Use when the user names or links a failed workflow run, reports a failing scheduled/manual workflow, or asks for end-to-end Actions recovery without further confirmation.
argument-hint: "[workflow run number, run URL, or workflow name]"
---

Rescue this failed GitHub Actions workflow end to end: **{{args}}**

Invocation authorizes the full loop — edits, tests, commits, pushes, PR
creation, squash merge, workflow dispatch/rerun, and cleanup — without pausing
for confirmation. Stop only on a real blocker (missing auth or secrets, or risk
of breaking `main`, weakening security/hygiene gates, or corrupting outputs)
and report it precisely.

## 1. Anchor target and state

Resolve the run live from GitHub (`run_number` like `#523` differs from the
API `run.id`). Use authenticated `gh` when available, or public GitHub APIs for
metadata plus an authenticated browser for logs, PRs, and manual dispatch; keep
credentials out of command output and URLs.

- Run `git status --short`, `git branch --show-current`, and
  `git log --oneline -3`.
- Record workflow path, run number/ID, head SHA/branch, failing jobs/steps,
  and URL. Compare recent runs across the last-success → first-failure
  boundary (runtime/dependency versions and error signatures).
- Read `.github/workflows/<workflow>.yml` and governing docs (`AGENTS.md`,
  `docs/lint-and-quality.md`, `docs/js-testing.md`, `docs/gotchas.md`).
- Check overlapping PRs with `python3 tools/prior_prs.py` (or the public pulls
  API if `gh` is unauthenticated).

## 2. Reproduce before theorizing

Read the failing step log bottom-up: Actions echoes every shell line in cyan
(`[36;1m`), including `echo "::error::..."` strings inside untaken branches, so
anchor on the step ending in `##[error]Process completed with exit code 1`. A
fast failure precedes the test suite; a segfault or import error before the
first print points to runtime or dependencies.

Build the tightest deterministic local loop from the repo root (using
`.venv/bin/python3` for Python; watch it fail before the fix, pass after):

1. Scoped regression test at the real call site
   (`make test-py SUITE=<addon>/tests`,
   `node --experimental-vm-modules --no-warnings tests/<file>.test.mjs`, or
   `NODE_OPTIONS="--experimental-vm-modules --no-warnings" npx jest review_heatmap/tests/<file>`).
2. Matching `make` gate or audit target (`fmt-check`, `lint`, `depcheck`,
   `typecheck-js`, `quality-py`, `check`, `sync-check`, `thinking-check`,
   `bot-pr-check`, `mutate-py`, `pip-audit`, `npm audit`).
3. Clean isolated env matching failing dependency/Node/Python versions (check
   `node -p process.execPath` per `docs/gotchas.md` if Jest ESM fails under a
   shim `node`).
4. Replay of a captured workflow payload, audit JSON, or artifact.
5. Workflow rerun only when no local seam exists.

Keep temporary venvs/logs out of tracked trees and delete them afterward. For
tricky failures use `diagnosing-bugs`.

Classify before editing:

- **Repository defect:** minimal root-cause fix + regression test.
- **Runtime/dependency/action rollover:** correlate versions at the failure
  boundary; pin a supported runtime, dependency, or action version (verify
  action tags via `gh api repos/<owner>/<repo>/git/refs/tags/v<N>`, and keep
  `"jsdom": "27.0.0"` exact per `docs/js-testing.md`).
- **Transient GitHub/registry outage:** rerun the failed jobs; skip creating a
  code change or empty PR.
- **Gate/audit failure:** keep `VERIFY_GATE`, `pip-audit`,
  `tools/check_bot_pr_hygiene.py`, and coverage floors intact; fix the
  underlying lockfile, code, or hygiene issue.
- **Red PR check (event payload or Dependabot):** checks reading the event
  payload replay the old payload on `gh run rerun` — retrigger with a fresh
  event (force-push, or `gh pr close` + `gh pr reopen`). When `gh pr edit`
  hits GraphQL `read:org` scope errors, use
  `gh api -X PATCH repos/<owner>/<repo>/pulls/<N> -f title="..."`. For a
  Dependabot bump failing on an existing file, reproduce with `npm ci` on the
  PR lockfile in a worktree, fix on the branch, and push an additive commit so
  Dependabot's signed commit stays intact.

## 3. Fix, prove, and ship

Follow AGENTS.md (shared checkout, single concern on a branch off `main`, one
conventional commit, PR body with What & why / Verification / Visual, `data/`
and vendored trees untouched).

- Prefer structural prevention (verified action SHA/tag pins, dependency pins,
  schema checks, validation) over prose.
- Add a regression test for each behaviour fix (JS tests run only under root
  `tests/` or `review_heatmap/tests/`; Python tests run via
  `.venv/bin/python3 -m pytest` from repo root).
- Run `make fmt`, `make fmt-py`, `make lint-fix`, and
  `python3 tools/sync_commands.py` as needed, then run
  **`make precommit SKIP=1`** on the finished committed tree (use
  `python3 tools/gate_guard.py snapshot` / `check` when iterating on a red
  gate; leave `make precommit-fix` `YOLO=1`/`MSG=` out of shared checkouts).
  If the command hits an execution cap, run every remaining `VERIFY_GATE`
  target separately and report exact results.
- Push, open a PR (draft only if visual review is needed), wait for all
  required checks (`ci.yml`, `security-check.yml`, `codeql.yml`,
  `dependency-review.yml`), amend + `git push --force-with-lease` on fixes,
  then squash-merge and confirm the merged SHA on GitHub.
- Return to a clean `main` (`git pull --rebase origin main`), keeping any
  branch or worktree holding unshipped or foreign work.

## 4. Execute on merged `main` and verify downstream outputs

Trigger or monitor the fixed workflow on merged `main` (`gh workflow run
<workflow>.yml --ref main` for dispatchable workflows such as `pages.yml`,
`mutation-testing.yml`, `dependency-auto-resolver.yml`,
`security-auto-fix.yml`, or inspect the `push` run on the merge SHA for
`ci.yml`, `security-check.yml`, `codeql.yml`, `pages.yml`). Resolve the new
run number/ID from its head SHA and monitor with bounded backoff; if it fails,
loop back to step 2 automatically.

Verify downstream outputs (`data/anki/` stats are generated locally via
`make fetch`, not by Actions):

- **`pages.yml`:** confirm deployment succeeded for the latest `main` SHA and
  the deployed `sw.js` stamps `CACHE_NAME` with `anki-cache-<short-sha>`.
- **`ci.yml` / `security-check.yml` / `codeql.yml`:** confirm all jobs on
  merged `main` (and unblocked PRs) pass, `npm-audit-results` / CodeQL SARIF
  uploads succeed, and `pip-audit` reports zero known vulnerabilities.
- **`mutation-testing.yml`:** confirm `mutmut-report` artifact uploaded and
  `.mutmut-cache` saved/restored cleanly.
- **`dependency-auto-resolver.yml` / `security-auto-fix.yml`:** inspect any
  created/updated PR (`automation/dep-resolution`, `security/npm-audit-fix`),
  confirm `"jsdom": "27.0.0"` stays exact, and verify its `ci.yml` checks pass.

Complete recovery for any missed-run backlog (stale Pages deploys, unmerged
automated fixes, missing artifacts) before finishing.

## 5. Evidence report

The rescue finishes only when the fixed workflow succeeds on merged `main` and
downstream outputs/deployments are verified. Clean up temp files, re-anchor
with `git status` and `git log`, and report:

1. Root cause and failing step.
2. Code/config fix and regression evidence.
3. PR number and merge commit.
4. Fresh run number/ID and result on `main`.
5. Verified downstream outputs (Pages deployment / `sw.js` stamp, artifacts,
   automated PRs, or security/CI status).
6. Any external limitation or unrecovered item.
