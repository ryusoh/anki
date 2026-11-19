---
name: gh-action-rescue
description: Fully diagnose and repair a failed GitHub Actions workflow run, then automatically verify, commit, push, open and merge a PR, and trigger/verify a fresh run or deployment. Use when the user names or links a failed workflow run, reports a failing scheduled/manual workflow, or asks for end-to-end Actions recovery without further confirmation.
argument-hint: "[workflow run number, run URL, or workflow name]"
---

Rescue this failed GitHub Actions workflow end to end: **{{args}}**

Invocation explicitly authorizes edits, tests, commits, pushes, PR creation,
squash merges, workflow dispatches/reruns, and cleanup. Do not ask for further
confirmation. Stop only for a real blocker such as unavailable authentication,
missing required secrets, or evidence that recovery would break `main`, weaken
security/hygiene gates, or corrupt generated outputs; report that blocker
precisely.

## 1. Anchor the target and current state

Re-resolve the run from GitHub rather than trusting a stale page or run title.
A workflow `run_number` (for example #523) is not the API `run.id`.

```bash
git status --short
git branch --show-current
git log --oneline -3
```

- Record the workflow name/path, run number and ID, head SHA/branch, failing
  jobs/steps, conclusion, and HTML URL.
- Check recent runs to find the last success and first consecutive failure.
  Compare dependency/runtime versions and error signatures across that boundary.
- Read the workflow YAML (`.github/workflows/<workflow>.yml`) and the governing
  docs before editing (`AGENTS.md`, `docs/lint-and-quality.md`,
  `docs/js-testing.md`, `docs/gotchas.md`).
- Check open/recently closed PRs for overlapping work using
  `python3 tools/prior_prs.py`; if unauthenticated `gh` makes it fail, query the
  public pulls API instead.
- Create a todo list covering diagnosis, fix/regression tests, shipping, fresh
  workflow execution, and downstream output/deployment verification. Keep
  exactly one item in progress.

Use authenticated `gh` when available. Otherwise use public GitHub APIs for run
metadata and an authenticated browser for logs, PR creation/merge, and manual
dispatch. Never print credentials or place API keys in URLs.

## 2. Establish the failure before theorizing

Read the actual failing step log bottom-up. Capture the first actionable error,
final exit status, runtime/dependency versions, and whether the script started
producing output. Actions echoes every line of a `run:` script in cyan
(`[36;1m`), including `echo "::error::..."` strings inside untaken branches —
match the step above `##[error]Process completed with exit code 1`, not echoed
script text. A fast failure usually precedes the test suite; a segfault or
import error before the first program print points to runtime/dependencies, not
later business logic.

Build the tightest deterministic loop that exercises this exact symptom (always
run from the repo root, using `.venv/bin/python3` for Python):

1. scoped regression test at the real call site (`make test-py SUITE=<addon>/tests`,
   `node --experimental-vm-modules --no-warnings tests/<file>.test.mjs`, or
   `NODE_OPTIONS="--experimental-vm-modules --no-warnings" npx jest review_heatmap/tests/<file>`);
2. matching `make` gate or audit target (`fmt-check`, `lint`, `depcheck`,
   `typecheck-js`, `quality-py`, `check`, `sync-check`, `thinking-check`,
   `bot-pr-check`, `mutate-py`, `pip-audit`, `npm audit`);
3. clean isolated environment reproducing resolved dependency/Node/Python
   versions (check `node -p process.execPath` per `docs/gotchas.md` if Jest ESM
   fails under a shim `node`);
4. replay of a captured workflow payload, audit JSON, or artifact;
5. workflow rerun only when no local seam exists.

Watch the loop fail before the fix and pass afterward. Keep temporary virtual
environments, logs, and diagnostic files out of tracked trees and delete them
afterward. For a difficult diagnosis, invoke `diagnosing-bugs` and rank 3–5
falsifiable hypotheses before probing.

Classify the result before changing files:

- **Repository defect:** fix the smallest root cause and add a regression test.
- **Runtime/dependency/action rollover:** correlate the first failure with
  resolved versions; pin a supported runtime, dependency, or action version
  (verify action tags exist via `gh api repos/<owner>/<repo>/git/refs/tags/v<N>`
  per `AGENTS.md`, and keep `"jsdom": "27.0.0"` exact per `docs/js-testing.md`).
- **Provider/registry outage or transient GitHub infrastructure failure with no
  code defect:** rerun the failed jobs; do not invent a code change or open an
  empty PR.
- **Gate/audit failure:** preserve the gate. Fix the underlying lockfile, code,
  or hygiene violation; never weaken `VERIFY_GATE`, `pip-audit`,
  `tools/check_bot_pr_hygiene.py`, or coverage floors to obtain green.

## 3. Fix and prove it

Make one concern-sized change on a branch off current `main`. Stage only files
owned by this rescue (`git add <file>`, never `git add -A`); concurrent agents
and the user may share the worktree. Never discard foreign changes or use
destructive git cleanup (`git checkout --`, `git restore`, `git reset --hard`,
`git clean`). Never hand-edit generated `data/` (`AGENTS.md` #4) or vendored
trees (`AGENTS.md` #5: `review_heatmap/libaddon/`, `_vendor/`).

For each behavior fix, include a test that fails before and passes after (JS
tests only execute under root `tests/` or `review_heatmap/tests/` per
`docs/js-testing.md`; Python tests run via `.venv/bin/python3 -m pytest` from
the repo root). Prefer structural prevention over prose: verified action
SHA/tag pins, dependency pins/overrides, schema checks, or validation.

If the fix edits Markdown, Python, or skills, run `make fmt`, `make fmt-py`,
`make lint-fix`, and `python3 tools/sync_commands.py` as needed. Then run
**`make precommit SKIP=1`** on the finished committed tree before opening a PR
(never run `make precommit-fix` with `YOLO=1` or `MSG=` in a shared worktree —
its commit step runs `git add -A`). When iterating on a red gate, use
`python3 tools/gate_guard.py snapshot` / `check` so an unchanged tree is never
rerun. If the command exceeds an execution cap, run every remaining
`VERIFY_GATE` target (`fmt-check`, `lint`, `typecheck-js`, `quality-py`, `check`,
`sync-check`, `thinking-check`, `bot-pr-check`) separately and report exact
results. Check the final diff for formatter damage, scratch artifacts, and
unrelated edits.

## 4. Ship without pausing

- Create one real conventional commit (`type(scope): summary`, imperative,
  lower-case, no trailing period, ≤ 72 chars); do not push empty/no-op commits.
- Push the branch and open a non-draft PR unless human visual review is
  required.
- Use a conventional PR title (≤ 72 chars, lower-case scope) and include **What &
  why**, exact **Verification** output (`make precommit SKIP=1` → green or scoped
  proof), and **Visual?** (`no visual surface` or `visual — human review required
(draft)`) in the body.
- Wait for all required checks (`ci.yml` `precommit`, `security-check.yml`,
  `codeql.yml`, `dependency-review.yml`, etc.). If red, inspect logs, fix on the
  same branch, rerun `make precommit SKIP=1`, amend/squash, and force-push with
  lease (`git push --force-with-lease`).
- Squash-merge only after required checks pass. Confirm the merged SHA through
  GitHub rather than inferring success from a button click.
- Confirm the local tree is clean, switch to `main`, and run:

```bash
git pull --rebase origin main
```

Do not delete branches or worktrees while they contain unshipped or foreign work.

## 5. Execute the fixed workflow

Trigger or monitor the fixed workflow on merged `main` (`gh workflow run
<workflow>.yml --ref main` for dispatchable workflows such as `pages.yml`,
`mutation-testing.yml`, `dependency-auto-resolver.yml`, `security-auto-fix.yml`,
or inspect the `push` run on the merge SHA for `ci.yml`, `security-check.yml`,
`codeql.yml`, `pages.yml`). Do not treat rerunning the old failed SHA as proof of
the fix.

Resolve and record the new run number and ID from its head SHA. Monitor every
material stage: checkout/action setup, dependency install (`npm ci`, `pip`),
checks/scans/mutation run, artifact upload, automated PR creation, and Pages
deployment. If this run fails, return to step 2 with its new logs and continue
automatically. Respect API/provider rate limits and use bounded backoff rather
than tight polling or retry loops. Do not weaken checks or manually mark a run
successful.

## 6. Verify downstream outputs and recovery

Verify every output or downstream effect owned by the rescued workflow (note that
`data/anki/` stats are generated locally via `make fetch` from the user's Anki
collection, not by GitHub Actions — never hand-edit `data/`):

- **`pages.yml`:** confirm the deployment succeeded for the latest `main` SHA,
  and inspect the deployed `sw.js` to confirm `CACHE_NAME` is stamped with the
  matching short commit SHA (`anki-cache-<short-sha>`) and wasn't left behind by
  a canceled run.
- **`ci.yml` / `security-check.yml` / `codeql.yml`:** confirm all jobs on merged
  `main` (and any open PRs unblocked by the fix) pass, `npm-audit-results` /
  CodeQL SARIF uploads succeed, and `pip-audit` reports zero known
  vulnerabilities.
- **`mutation-testing.yml`:** confirm `mutmut-report` artifact uploaded and
  `.mutmut-cache` saved/restored cleanly.
- **`dependency-auto-resolver.yml` / `security-auto-fix.yml`:** if the workflow
  creates or updates an automated PR (`automation/dep-resolution` or
  `security/npm-audit-fix`), inspect the PR diff (confirm `"jsdom": "27.0.0"`
  remains exact) and verify its `ci.yml` checks run green.

If missed runs left pending work behind (such as stale Pages deploys, unmerged
automated dependency/security fixes, or missing artifacts), complete recovery for
the full pending state rather than stopping at a partial check. Never invent
data or suppress audit findings to force green.

## 7. Finish only with evidence

The rescue is incomplete until the fixed workflow has actually succeeded on
merged `main` and required outputs/deployments are verified.

Respond with:

1. root cause and failing step;
2. code/config fix and regression evidence;
3. PR number and merge commit;
4. fresh run number/ID and result on `main`;
5. verified downstream outputs (Pages deployment / `sw.js` stamp, artifacts,
   automated PRs, or security/CI status);
6. any external limitation or unrecovered item, without guarantees that every
   future third-party outage is impossible.

Clean up temporary environments and diagnostic files. Update the todo list and
re-anchor from `git status` and `git log` before reporting completion.
