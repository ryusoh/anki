---
name: bot-pr-rescue
description: Diagnose and salvage a failing Jules/bot PR — identify which gate failed, reproduce it locally, decide salvage vs close, and squash-force-push the fix. Use when the user pastes a Jules branch name, task id, or a bot PR with red CI.
argument-hint: "[PR number, branch name, or Jules task id]"
---

Rescue a failing bot PR (Jules routines: bolt, janitor, palette, refactoring,
sentinel, testpilot, typist). Motivating incidents: PR #494 here (five
empty/churn commits after review questions — closed unmerged) and fund#692
(per-commit hygiene gate red despite a clean final tree).

## 1. Identify the PR

A branch named `<kebab-slug>-<19-20 digit number>` is a **Jules branch** — the
trailing number is the Jules task id (`https://jules.google.com/task/<id>`).
Don't grep the repo for it; go straight to GitHub:

```bash
gh pr list --limit 15                       # branch column shows the slug
gh pr view <N> --json title,headRefName,mergeable,mergeStateStatus,files
gh pr checks <N>                            # which check is red
```

## 2. Diagnose the failing check

```bash
gh pr checks <N>                            # take the failing job's run URL
gh run view --job=<job-id> --log | grep -iE "fail|error" | head
```

**Gotcha — script echoes look like errors.** Actions echoes every line of a
`run:` script in cyan (`[36;1m`), including `echo "::error::..."` strings
inside if-branches that never executed. The real failure is the step whose
**own output** ends in `##[error]Process completed with exit code 1`. Read the
log bottom-up and match the error to the step above it, not to any cyan line.

Know the two fast gates that run before the test suite in the `ci.yml`
`precommit` job (a failure in the first minute is one of these, not tests):

- **Reject empty pull request** — `git diff --quiet origin/<base>` at the merge
  ref. Fires when the PR's _net_ diff vs current main is empty, i.e. the work
  is already on main (duplicate) or the branch is a no-op. Not fixable by the
  bot — close the PR.
- **Reject bot PR hygiene violations** — `tools/check_bot_pr_hygiene.py`,
  **per-commit**: empty commits, zero-content files, test files with deleted
  lines (bot lanes are append-only in tests), stray artifacts (`pr_body.txt`,
  `*.log`, `*_output.txt`, `*_out.json`, ...), `eslint-suppressions.json` ratchet. A
  violation reverted by a later commit still fails — only squashing recovers
  it.

Everything after those two steps is the full `make precommit SKIP=1` suite
(fmt-check, lint, typecheck-js, quality-py, check, sync-check, thinking-check,
bot-pr-check) — reproduce those failures with the matching `make` target.

## 3. Reproduce locally

```bash
git fetch origin pull/<N>/head:pr<N>-head
git worktree add /tmp/pr<N> pr<N>-head --detach -f
cd /tmp/pr<N> && python3 tools/check_bot_pr_hygiene.py --base origin/main
```

**Worktree gotchas:** committing in a worktree triggers the repo's
`.git/hooks/pre-commit` hook (hooks live in the shared git dir), which runs the
full `make precommit` — use `git -c core.hooksPath=/dev/null commit` for the
squash commits below. Worktrees also lack `.venv` and `node_modules`; symlink
them from the main checkout before running tests:

```bash
ln -s /Users/lz/dev/anki/.venv .venv
ln -s /Users/lz/dev/anki/node_modules node_modules
```

## 4. Assess salvageability

Squash-simulate and re-run the gate — if the final tree is compliant, the
per-commit violations die with the history:

```bash
cd /tmp/pr<N>
git reset --soft $(git merge-base origin/main HEAD)
git -c core.hooksPath=/dev/null commit -m "<conventional subject>"
python3 tools/check_bot_pr_hygiene.py --base origin/main
```

Then verify the content against **current main** (the bot's base may be stale):

```bash
git worktree add /tmp/pr<N>-main origin/main --detach -f
cd /tmp/pr<N>-main
git checkout pr<N>-head -- <changed files>
ln -s /Users/lz/dev/anki/.venv .venv && ln -s /Users/lz/dev/anki/node_modules node_modules
.venv/bin/python3 -m pytest <changed python test files>   # run from the worktree root
```

Decide: net diff vs `origin/main` empty → **close as duplicate**. Content good
→ salvage (step 5). Content bad → close with a one-line reason.

## 5. Salvage

Work in the `/tmp/pr<N>` worktree (detached HEAD). Do **not** `git checkout -b`
a salvage branch in the main worktree — that hijacks the branch the user's
checkout is on; squash on the detached HEAD and push it directly:

```bash
git fetch origin <pr-branch>:refs/remotes/origin/<pr-branch>   # enables --force-with-lease
cd /tmp/pr<N>
pr_author=$(gh api repos/<owner>/<repo>/pulls/<N> --jq '.user.login')
pr_author_id=$(gh api repos/<owner>/<repo>/pulls/<N> --jq '.user.id')
git reset --soft $(git merge-base origin/main HEAD)
git -c core.hooksPath=/dev/null commit \
  --author="$pr_author <$pr_author_id+$pr_author@users.noreply.github.com>" \
  -m "<conventional subject>" \
  -m "Co-authored-by: $(git config user.name) <$(git config user.email)>"
git push --force-with-lease origin HEAD:<pr-branch>
gh pr checks <N>                    # wait for precommit green
gh pr merge <N> --squash --delete-branch
git checkout main && git pull --rebase origin main
git branch -D pr<N>-head
git worktree remove /tmp/pr<N> --force; git worktree remove /tmp/pr<N>-main --force
```

The replacement commit must preserve the original PR author with `--author`;
the rescuer's identity belongs in `Co-authored-by`. For a Jules PR this
resolves to `google-labs-jules[bot] <161369871+google-labs-jules[bot]@users.noreply.github.com>`.
Do not rely on GitHub's squash-merge UI to repair attribution after the push.

The PR title must stay a valid Conventional Commit subject — it becomes the
squash-merge commit message.

**Gotcha — this repo has no PR-title CI check** (unlike fund's
`commit-lint.yml`); the title is only judged at squash-merge review against
the AGENTS.md conventions (`type(scope): summary`, imperative, ≤ 72 chars,
lower-case scope). Count the assembled subject's characters before pushing —
fund#695's 73-char camelCase-scope title failed fund's title gate. The general
rule still applies to any check that reads the event payload: `gh run rerun`
replays the OLD payload, so retrigger with a fresh event (a force-push, or
`gh pr close` + `gh pr reopen`), never a rerun. When `gh pr edit` fails with
GraphQL scope errors (`read:org`), use
`gh api -X PATCH repos/<owner>/<repo>/pulls/<N> -f title="..."` instead.

## 6. Fix forward (the compounding loop)

A rescued PR means the harness allowed dirty history to be produced or pushed.
Patch the root cause with **compounding mechanical fixes**, not ceremonial
instruction:

- **Anti-pattern — do NOT performatively cite PR numbers:** Do not append PR
  citations (e.g. `(PR #XYZ failed...)`) to `.jules/*.md` personas just to
  "do something". Citing past failures in LLM prompt files creates prompt bloat
  and warning fatigue without improving agent compliance. Fixes must be
  mechanical and structural.
- **Level 1: Mechanical prevention (`.gitignore`):** If a stray artifact
  (`*.log`, `*_output.txt`, `*.tmp`, `commit_message.txt`) was committed,
  ensure it is ignored in `.gitignore`. When git ignores the pattern, even
  clumsy staging (`git add .`) cannot stage the artifact, preventing the
  failure at the source.
- **Level 2: Gate & invariant lock (`check_bot_pr_hygiene.py`):** If a new
  stray artifact pattern was missed, widen `_is_stray_artifact` and ensure
  `test_all_stray_artifact_patterns_are_gitignored` in
  `tools/test_check_bot_pr_hygiene.py` passes so the gate and `.gitignore`
  never drift out of sync.
- **Level 3: Persona instruction (structural, not ceremonial):** Only edit
  `.jules/<routine>.md` if an operational rule or workflow step was genuinely
  missing or incorrect — never add incident tombstones.

Run `python3 tools/sync_commands.py` after editing any skill to keep
`.claude/commands/` in sync. Run `make precommit SKIP=1` green before committing.
Note in the commit body when the edit touches a persona or skill file.
