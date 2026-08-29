# Cross-cutting gotchas

Operational traps and historical fixes that apply across the repo. Binding
rules still live in `AGENTS.md`; this page is the reference for why the trap
exists and how to avoid it.

## `make precommit-fix` is NOT a dry run under `make -n`

GNU make executes `$(MAKE)`-bearing recipe lines even under `-n`, and the
`precommit-fix` recipe is one such compound command — a "dry run" used to really
commit and push. The Makefile now refuses `-n`/`-q`/`-t` for this target at
parse time (`tests/test_makefile_dryrun_guard.py` pins it).

To verify recipe changes, extract and `sh`-execute snippets in a test instead
(`tests/test_makefile_push_gate.py` shows the pattern).

## `precommit-fix` with `YOLO=1`/`MSG=` runs `git add -A`

The commit step stages **everything** in the working tree, not just what this
invocation touched. If another process (a concurrent agent session, a background
task without worktree isolation) has unrelated uncommitted changes sitting in
the checkout when it runs, they get swept into that commit under an unrelated
message (observed 2026-07-13, commit `e3800278`).

Check `git status` before running `precommit-fix` with `YOLO=1`/`MSG=`, and
prefer worktree isolation for any spawned session that might invoke it.

## Concurrent agents sharing one worktree

When running parallel subagents (swarms, background agents) in this checkout:

- Stage only files you changed (`git add <specific-files>`, never `git add -A`).
- Never `git stash`, `git reset --hard`, or `git commit --no-verify` — a sibling
  agent's work may be sitting in the same tree.
- Keep concurrent agents on disjoint file sets; if a rebase/conflict lands
  mid-run, resolve only files your task owns.
- Never let a spawned session run `precommit-fix` with `YOLO=1`/`MSG=` against
  the shared checkout — its commit step is `git add -A` (see above).

## Limited / slow network

`precommit-fix` pushes via `tools/git_push_retry.py` (backoff retries +
per-commit chunking; run it directly to drain unpushed commits) and caps its
backgrounded R2/graph uploads at `NET_DEADLINE` seconds (default 1800; raise with
`NET_DEADLINE=3600` to let a slow upload finish). Failures are loud, never
silent, and reruns resume incrementally.

Full map: [`docs/limited-network.md`](limited-network.md).

## Graph scripts are standalone scripts

Any script under `graph/` that imports sibling modules (`from graph.builder
import ...`) must insert the repo root into `sys.path` _before_ those imports.
See [`docs/graph-analysis-guide.md`](graph-analysis-guide.md).

## The user commits reviewed changes themselves

The user's work pattern is: back-and-forth in chat → they review the diff in
VSCode → they commit it themselves and move on. So if your edits vanish from
`git status` between turns, run `git log --oneline -3` first — a fresh user
commit containing them means the work was accepted. Don't re-verify, re-explain,
or dig into "where did my changes go"; check the log once and continue from
HEAD.

## Never discard uncommitted user work without explicit confirmation

`git checkout -- <file>`, `git reset --hard`, and similar destructive resets can
destroy changes the user made in another session or is still reviewing. This is
especially risky in `data/`, where the "never hand-edit generated data" rule
means _agents shouldn't create manual edits there_, not that an agent may freely
revert whatever is uncommitted. If you see uncommitted changes and don't know
their origin, ask before resetting.

## Skill and command regeneration

A running agent session sees skills as of session start. Editing or syncing
`.agents/skills/` mid-session does not change what the running session has
loaded — an invoked skill still uses the pre-edit text (observed: `/retro`
loading a pre-consolidation copy). Start a new session to pick up skill edits.
