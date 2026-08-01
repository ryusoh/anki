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

**Run the tool from a branch.** It is meant for the normal commit/push path;
if invoked from a detached HEAD it exits with an error and advises
`git push origin HEAD:<branch-name>` instead of retrying blindly.

Pinned by `tests/test_git_push_retry.py` and `tests/test_makefile_push_gate.py`.

## Failure mode 2: background uploads hang the run forever

`precommit-fix YOLO=1` backgrounds the R2 upload and the public graph push,
then `wait`s on them last. Their clients have 120s per-request timeouts, but
on a slow-but-alive link bytes keep flowing, so no timeout ever fires — the
run appeared to hang forever right after the graph-local log.

Each job now runs under its own `tools/run_with_deadline.py` wrapper (a
portable `timeout(1)`; macOS ships none), capped at `NET_DEADLINE` seconds
(default 1800). At the deadline the job's whole process group is
TERM→KILLed, the job exits 124, and the run fails loudly with rerun advice.
Both uploads are incremental — rerunning `make fetch-r2-skip-fetch` /
`make graph-push` on a healthy network resumes where they got to.

The two network jobs no longer share a single deadline: a slow R2 upload
cannot starve the public graph push (or vice versa).

Let a slow-but-working upload finish by raising the cap:

```sh
make precommit-fix YOLO=1 NET_DEADLINE=3600
```

Pinned by `tests/test_run_with_deadline.py` and
`tests/test_makefile_net_deadline.py`.

## Failure mode 3: `git push` rejected with "fetch first" / non-fast-forward

`make precommit-fix YOLO=1` pushes after a long fix-and-verify run. If another
client pushed to `main` in the meantime, the remote tip is ahead of the local
tracking ref and the push is rejected:

```
! [rejected]  main -> main (fetch first)
```

`tools/git_push_retry.py` now accepts `--auto-rebase`. In the unattended
commit/push path (`YOLO=1` or `MSG=`) `precommit-fix` passes this flag, so the
script:

1. fetches to refresh the remote-tracking ref;
2. if upstream is ahead, runs `git pull --rebase` once;
3. retries the push loop from the top.

If the rebase hits a conflict, it runs `git rebase --abort` and exits non-zero
so the working tree is never left half-merged. The failure is then loud and
manual resolution is required.

Drain a backlog this way by hand:

```sh
python3 tools/git_push_retry.py --auto-rebase
```

Pinned by `tests/test_git_push_retry.py` (unit + integration) and
`tests/test_makefile_push_gate.py`.

## Failure mode 4: direct connections blocked — local proxy fallback

Sometimes the uplink only works through a local proxy client
(Clash Verge et al.), and sometimes a stale `HTTPS_PROXY` export points at a
proxy that is no longer listening — observed 2026-07-17, when a dead proxy
env var failed **every** upload in a run with
`Failed to connect to proxy URL`. Network callers in this repo therefore
self-heal in **both** directions: try the configured route first, and on
failure probe well-known localhost proxy ports (`7897`, `7890` — Clash
Verge/Clash mixed; `1087` — ShadowsocksX-NG HTTP; `8118` — Privoxy; `3213` —
Astrill OpenWeb) or fall back to a direct connection.

`shared/proxy_fallback.py` is the canonical implementation. Anki add-ons
must be self-contained (AnkiWeb packages ship a single add-on dir), so each
consuming add-on keeps a byte-identical vendored copy at
`<addon>/proxy_fallback.py` and imports it with
`from .proxy_fallback import urlopen_with_proxy_fallback`.
`tests/test_proxy_fallback_sync.py` pins the vendored copies byte-identical
to the canonical file and the port lists everywhere identical — edit the
canonical file, re-copy it to every add-on, and sync the port list in
`data/anki/upload-to-r2`:

- `shared/proxy_fallback.py` (+ vendored copies in `auto_wiktionary/` and
  `auto_image/`) — `urlopen_with_proxy_fallback()` runs **inside Anki**, so
  the proxy is scoped to a cached urllib opener instead of `os.environ`
  (never leak a proxy to the whole Anki process). HTTP 4xx/5xx bypass the
  fallback (they reached the server); a dead cached proxy heals back to
  direct. If the first direct attempt fails, it retries once with a
  **proxy-free opener** before probing ports — `urllib.request.urlopen`'s
  global opener snapshots the system proxy at first use, so a proxy that was
  live when Anki started but is now gone (Astrill OpenWeb switched off or to
  WireGuard/tunnel mode) otherwise breaks every later call with
  `Network connection failed` even though browsers work (observed
  2026-08-01). Pinned by each addon's `tests/test_proxy_fallback.py`.
- `data/anki/upload-to-r2` — standalone script with its own inline helper:
  `enable_proxy_fallback()` exports the detected proxy into
  `HTTPS_PROXY`/`HTTP_PROXY` for the rest of the process (botocore reads env
  at client creation; the urllib fallback rebuilds its opener). A
  configured-but-dead proxy is dropped and the run retries direct. Also used
  by `graph/upload_public.py`. Pinned by
  `data/anki/tests/test_proxy_fallback.py`.

### Which VPN mode needs what (observed 2026-07-18)

- **Clash Verge**: sets the system proxy and listens on its mixed port —
  the fallback covers it.
- **Astrill OpenWeb mode**: sets the macOS system proxy to `127.0.0.1:3213`;
  only apps honoring the system proxy (browsers) get through. Local DNS
  still returns poisoned IPs for blocked hosts, so a no-proxy HTTPS
  connection dies with a TLS handshake timeout. And because
  `urllib.request.urlopen`'s global opener snapshots the system proxy at
  first use, a proxy set _after_ process start (Anki launched before
  Astrill) is never picked up — the `3213` probe is what heals it.
- **Astrill StealthVPN / other tunnel modes**: full-tunnel `utun` with VPN
  DNS — direct connections just work, no local proxy exists, and the
  fallback never triggers (a proxy cached from an earlier OpenWeb session is
  dropped by the dead-proxy healing back to direct).

### What the fallback can't cover: Anki's native sync

`urlopen_with_proxy_fallback()` only wraps Python `urllib` calls made by
add-on code. Anki's native collection/media sync runs in Anki's **Rust
core** (reqwest), outside the Python runtime, so no add-on can intercept or
retry it. The symptom on a blocked route (reported 2026-07-19) is the
localized sync dialog:

```
ネットワークのエラーが発生しました。
エラー詳細: error sending request for url ()
```

`error sending request for url ()` is a reqwest error string, not urllib —
the empty `url ()` means the connection died before a request was even sent
(DNS/TCP/TLS), which is what a poisoned direct route to AnkiWeb looks like.
Fixes, in order of least friction:

- **TUN/enhanced mode in the VPN client** routes all system traffic
  including sync — no Anki-side configuration needed.
- **Launch Anki with proxy env vars** — the Rust backend reads the standard
  `HTTPS_PROXY`/`HTTP_PROXY` variables:

  ```sh
  HTTPS_PROXY=http://127.0.0.1:7897 HTTP_PROXY=http://127.0.0.1:7897 \
    /Applications/Anki.app/Contents/MacOS/anki
  ```

  `open -a Anki` does not propagate env vars — launch the binary directly.

- The macOS system proxy alone may not be honored by the Rust backend, so
  prefer one of the two routes above.

Verify a fallback change against the live VPN by simulating the broken
direct path — force a no-proxy connection with
`build_opener(ProxyHandler({}))`, or in a Python session:

```python
with patch('urllib.request.urlopen', side_effect=URLError(TimeoutError('handshake timed out'))):
    utils.fetch_wiktionary_html('猫', 'ja')  # must heal via the detected proxy
```

**Keep fallback tests hermetic.** The helper has three network paths, and a
test that patches only `urllib.request.urlopen` silently hits the real
network through the other two. Any failure-path test must patch all of:
`urllib.request.urlopen`, `<addon>.proxy_fallback._build_direct_opener`, and
`<addon>.proxy_fallback._detect_local_proxy` (plus
`urllib.request.build_opener` when asserting the proxy opener). See
`auto_wiktionary/tests/test_proxy_fallback.py` for the pattern. When adding a
new path to the helper, grep for `side_effect=URLError` across `*/tests/` and
patch the new path everywhere.

**Diagnosing a live failure** (browser works, add-on says network error) —
rule the environment in or out before touching code:

```sh
for p in 7897 7890 1087 8118 3213; do nc -z -w 1 127.0.0.1 $p && echo "$p open"; done
python3 -c "import urllib.request; print(urllib.request.getproxies())"
curl -sS -o /dev/null -w '%{http_code} total=%{time_total}s\n' --max-time 15 \
  'https://en.wiktionary.org/api/rest_v1/page/html/test'
```

All ports closed + `getproxies()` empty + curl 200 means the add-on's failure
is a stale snapshot or timeout, not the network — and since 2026-08-01 the
Wiktionary tooltip includes the underlying `URLError` reason
(`Error: Network connection failed. (<reason>)`), which distinguishes DNS,
connection-refused, and timeout at a glance.

Related invariant, pinned by `data/anki/tests/test_failed_upload_hash_map.py`:
**failed uploads never enter the hash map**, so an interrupted or partly
failed run retries exactly the missing files on rerun. Audit the ledger
against the live bucket any time with:

```sh
make verify-r2    # read-only; exit 2 lists poisoned entries + fix advice
```

(`.make/r2-upload.log` is overwritten by each `precommit-fix` run — when
diagnosing an _older_ run, the bucket audit above is the reliable source,
not the log.)

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
