---
name: debug-proxy
description: Debug an add-on network failure (errno 61 connection refused, timeouts) when the browser works but the add-on doesn't — rule the environment in or out, reproduce Anki's stale-proxy process state live, TDD a fix in shared/proxy_fallback.py, and re-vendor the copies. Use when auto_wiktionary/auto_image/auto_itaigi/awesome_tts report "Network connection failed" on a healthy network.
---

# Debug an add-on proxy/network failure

Symptom shape: `Error: Network connection failed. (<reason>)` from an add-on
while the same site loads fine in Chrome. The reason string distinguishes the
families at a glance: `[Errno 61] Connection refused` = dialing a dead
localhost proxy; timeout = poisoned direct route; DNS = resolution. Full
background: `docs/limited-network.md`, failure mode 4.

Work environment-first: prove the network healthy before touching code.

1. **Rule the environment in or out.** Check the live proxy state and direct
   reachability:

   ```sh
   scutil --proxy                       # macOS system proxy (HTTPEnable/HTTPSEnable)
   env | grep -i proxy                  # stale HTTP_PROXY/HTTPS_PROXY exports
   for p in 19750 7897 7890 1087 8118 3213; do nc -z -w 1 127.0.0.1 $p 2>&1 | sed "s/^/port $p: /"; done
   ```

   Then verify DNS, TCP, and HTTPS separately — a staged check localizes the
   failure instead of guessing:

   ```sh
   .venv/bin/python3 - <<'EOF'
   import socket, urllib.request
   infos = socket.getaddrinfo("en.wiktionary.org", 443, proto=socket.IPPROTO_TCP)
   print("DNS:", sorted({i[4][0] for i in infos}))
   s = socket.create_connection(infos[0][4], timeout=5); print("TCP ok"); s.close()
   req = urllib.request.Request("https://en.wiktionary.org/w/api.php?action=parse&page=test&prop=text&format=json&formatversion=2",
                                headers={"User-Agent": "AnkiAddon/1.0"})
   r = urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=10)
   print("HTTPS direct:", r.status, len(r.read()))
   EOF
   ```

   All proxy ports closed + direct HTTPS 200 + the add-on still failing means
   the bug is **process state inside Anki**, not the network.

2. **Understand the process-state failure mode.** `urllib.request.urlopen`'s
   global opener snapshots the system proxy **at first use**. If a proxy app
   (Clash on 7890, Astrill OpenWeb on 3213) was on when Anki made its first
   request and is later switched off, every urlopen dials the dead proxy →
   errno 61 — while Chrome, which re-reads proxy settings live, works fine.
   `urlopen_with_proxy_fallback` (in `shared/proxy_fallback.py`) exists to
   heal this: dead cached proxy → direct → proxy-free opener → probe local
   ports.

3. **Reproduce Anki's process state live.** Poison the global opener with a
   dead proxy, then call the add-on's real fetch. `import conftest` FIRST —
   the root `conftest.py` stubs `aqt`/`anki`, and forgetting it dies with
   `ModuleNotFoundError: No module named 'aqt'`:

   ```sh
   .venv/bin/python3 - <<'EOF'
   import conftest, urllib.request
   urllib.request._opener = urllib.request.build_opener(
       urllib.request.ProxyHandler({'http': 'http://127.0.0.1:7890', 'https': 'http://127.0.0.1:7890'})
   )
   from auto_wiktionary.utils import fetch_wiktionary_html
   html = fetch_wiktionary_html('test', 'en')
   print("starts with Error?", html.startswith("Error:"), "| bytes:", len(html))
   EOF
   ```

   If the fallback is working this prints `False` and a large byte count. If
   it prints the errno-61 error, the healing chain itself is broken — trace
   which retry stage fails by calling them individually
   (`urllib.request.urlopen`, `proxy_fallback._build_direct_opener().open(...)`,
   `proxy_fallback._detect_local_proxy()`).

4. **The gotcha that bit us (2026-08-07): ProxyHandler mutates the Request
   in place.** A failed proxied attempt rewrites `req.host` to the dead
   proxy host (`req._tunnel_host` keeps the real one), so **every retry with
   the same Request object keeps dialing the dead proxy** — the healing
   fallback could never heal. Verify mutation suspicion with:
   `print(req.host, getattr(req, '_tunnel_host', None))` before/after the
   first attempt. Retries must use a pristine clone (`_fresh_request`;
   `req.full_url` survives the mutation). Pinned by
   `auto_wiktionary/tests/test_proxy_fallback.py::test_retry_uses_pristine_request_after_proxy_mutation`.

5. **Fix test-first, in the canonical file only.**
   - Add the failing test to `<addon>/tests/test_proxy_fallback.py` and
     confirm it is **red** first. Keep tests hermetic: patch ALL network
     paths (`urllib.request.urlopen`, `_build_direct_opener`,
     `_detect_local_proxy`, plus `build_opener` when asserting the proxy
     opener) — patching only urlopen silently hits the real network through
     the other two.
   - Fix in `shared/proxy_fallback.py` (the CANONICAL source), then re-vendor
     byte-identical copies:

     ```sh
     for d in auto_wiktionary auto_image auto_itaigi awesome_tts; do cp shared/proxy_fallback.py "$d/proxy_fallback.py"; done
     ```

     `tests/test_proxy_fallback_sync.py` pins the copies byte-identical and
     the port list in sync with `data/anki/upload-to-r2`.

6. **Verify from the repo root:**

   ```sh
   make test-py SUITE=<addon>/tests
   .venv/bin/python3 -m pytest tests/test_proxy_fallback_sync.py -q
   make precommit SKIP=1
   ```

   Re-run the step-3 live repro — it must now heal.

7. **Report plainly** and remind the user to **restart Anki**: the running
   process has the old module cached, so it keeps erroring until reloaded.
   Mocked tests can't prove real-Anki behaviour.
