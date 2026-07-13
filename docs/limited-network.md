# Working on a limited / slow network

This machine regularly runs `make precommit-fix YOLO=1` over a trickling
uplink (observed 2026-07-13: 53 KiB/s). Two failure modes showed up, both now
handled by the Makefile; this page is the operator's map.

## Failure mode 1: `git push` dies with HTTP 408

A multi-MiB pack pushed over HTTPS gets `RPC failed; HTTP 408` once the
upload outlives the server's request window, and git HTTP uploads cannot
resume — all-or-nothing. Worse, the old recipe discarded the push result and
exited 0 with the commit silently unpushed.

`precommit-fix` now pushes through `tools/git_push_retry.py`:

- plain `git push` first;
- on failure with several commits queued, pushes them **one at a time,
  oldest first** — each is its own smaller HTTP request, and every chunk
  that lands stays landed, so retries only re-upload the remainder;
- retries with exponential backoff, forcing HTTP/1.1 + a large
  `http.postBuffer` (single buffered POST instead of chunked
  transfer-encoding);
- exits non-zero if the branch still isn't fully pushed, which fails the
  make target loudly (`PUSH_OK` guard).

Drain a backlog of unpushed commits by hand any time:

```sh
python3 tools/git_push_retry.py
```

A rerun of `precommit-fix` with nothing new to commit also retries the push
(an empty index skips `git commit` instead of aborting the chain).

Pinned by `tests/test_git_push_retry.py` and `tests/test_makefile_push_gate.py`.

## Failure mode 2: background uploads hang the run forever

`precommit-fix YOLO=1` backgrounds the R2 upload and the public graph push,
then `wait`s on them last. Their clients have 120s per-request timeouts, but
on a slow-but-alive link bytes keep flowing, so no timeout ever fires — the
run appeared to hang forever right after the graph-local log.

Both jobs now run under `tools/run_with_deadline.py` (a portable
`timeout(1)`; macOS ships none), capped at `NET_DEADLINE` seconds
(default 900). At the deadline the job's whole process group is
TERM→KILLed, the job exits 124, and the run fails loudly with rerun advice.
Both uploads are incremental — rerunning `make fetch-r2-skip-fetch` /
`make graph-push` on a healthy network resumes where they got to.

Let a slow-but-working upload finish by raising the cap:

```sh
make precommit-fix YOLO=1 NET_DEADLINE=3600
```

Pinned by `tests/test_run_with_deadline.py` and
`tests/test_makefile_net_deadline.py`.

## Related gotchas

- **`make -n precommit-fix` is NOT a dry run.** GNU make executes
  `$(MAKE)`-bearing recipe lines even under `-n`, and the recipe is one such
  compound command — a "dry run" used to really commit (and would have
  pushed). The Makefile now refuses `-n`/`-q`/`-t` for this target at parse
  time; pinned by `tests/test_makefile_dryrun_guard.py`. To verify recipe
  changes, extract and `sh`-execute snippets in a test instead (see
  `tests/test_makefile_push_gate.py` for the pattern).
- **Worktrees don't inherit `.venv` or `node_modules`** (both gitignored).
  Test suites run fine with `python3 -m pytest` from the worktree root, but
  for targeted lint/format runs call the binaries from the main checkout —
  `<main-checkout>/.venv/bin/ruff ...` or
  `npx --prefix "<main-checkout>" prettier ...` — instead of re-running
  `make install` per worktree.
- **New worktrees branch from local HEAD** (`worktree.baseRef: "head"` in
  `.claude/settings.json`): on this network `origin/main` is often behind
  local `main`, and branching from origin silently drops unpushed work.
