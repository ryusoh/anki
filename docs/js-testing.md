# JS testing: where tests run (and where they silently don't)

The Python side of this repo auto-discovers every `<addon>/tests/` suite. **The JS
side does not.** Exactly two locations are executed by `make check-node`:

1. **Root `tests/`** — `tools/node_test_runner.mjs` recursively scans _only_ the
   repo-root `tests/` directory for `*.test.js` / `*.test.cjs` / `*.test.mjs` and
   runs each file as a plain `node` process (`--experimental-vm-modules` for ESM).
2. **`review_heatmap/tests/`** — run separately via jest.

A `*.test.js` anywhere else is **silently never executed** — it shows up in
`git ls-files`, looks like coverage, and gates nothing. (This bit us:
`graph/tests/*.test.js` sat dead for months, importing modules that no longer
existed, and nothing failed.)

**Why `review_heatmap/tests/` isn't in the coverage numbers**: `make
check-node` runs it as a separate, uninstrumented `npx jest` invocation after
the root suite's `c8`/`node_test_runner.mjs` pass finishes — it's a pass/fail
gate only. The two suites use different runners (plain `node:test` vs. jest+
jsdom) with different coverage engines (`c8`/V8 vs. jest's own Istanbul), and
nothing merges the two reports. This is deliberate scope, not an oversight —
see the jsdom section below for why `review_heatmap/tests/` can't just move
onto the root runner.

**Worktree footgun (fixed 2026-07-11)**: `package.json`'s
`testPathIgnorePatterns` used to list a bare `/.claude/`, meant to stop jest
from crawling into nested Claude Code worktree copies of the repo (e.g.
`<repo>/.claude/worktrees/*`) when run from the main checkout. But an
unanchored `/.claude/` matches the _whole absolute path_ — so when the
checkout you're running tests from is itself inside `.claude/worktrees/...`
(true for every Claude Code coding session), it matched every single file and
jest silently reported "No tests found" for `review_heatmap/tests/` instead
of failing loudly. Now anchored as `<rootDir>/.claude/` /
`<rootDir>/.venv/`, which still excludes nested worktrees from the main
checkout but no longer nukes the whole suite when the checkout itself lives
under `.claude/`.

## Writing a root `tests/` JS test

- Use `node:test` + `node:assert` — **not** `@jest/globals`. The runner is plain
  node; jest-style named imports crash with
  `SyntaxError: Named export 'beforeEach' not found`.
- Run one file scoped (fast loop), from the repo root:

  ```sh
  node --experimental-vm-modules --no-warnings tests/<name>.test.mjs
  ```

  Full suite with coverage: `make check-node`.

- Testing `js/commands/{due,reviews,retention}.js`? Reuse
  `tests/helpers/chartDomMock.cjs` (`createChartDomMock()` for the
  `#runningAmountCanvas`/`#runningAmountSection`/`#chartLegend`/
  `#runningAmountEmpty` element mocks, `createMockChartClass()` for a
  `window.Chart` stub that records the last render config via
  `getLastConfig()`) instead of re-deriving this boilerplate — see
  `tests/due_calendar.test.cjs` / `tests/retention_calendar.test.cjs` for
  usage. Handler-level tests that also exercise scroll/zoom/dataset
  attributes use a different, broader element mock (see
  `tests/handler_calendar.test.cjs`) — that's a deliberate second idiom, not
  a gap to unify.

## jsdom version constraint (pinned to exactly 27.0.0)

`jsdom` is pinned to the **exact** version `27.0.0` in `package.json`
(`"jsdom": "27.0.0"`, no `^`) — a caret range will drift forward on
`npm install` and silently reintroduce the breakage below (this happened
once already: `^27.3.0` resolved to `27.4.0`, which is broken). **Do not
change the jsdom version, and do not add a `^`/`~`, without re-running
`NODE_OPTIONS="--experimental-vm-modules --no-warnings" npx jest
review_heatmap/tests/` and confirming both suites still pass.**

As of 2026-07-13, `check-node`'s Makefile target asserts `package.json`'s
`dependencies.jsdom` is exactly `"27.0.0"` before running anything else, and
fails loudly with a pointer back to this section if not — this catches the
jsdom-field-drift case (a bad dependabot/auto-resolver PR, a stray `^`)
regardless of CI's Node version (all four `.github/workflows/*.yml` pin
Node 24, which is why the original `ce967f67` bump's CI stayed green while
local `make check-node` on Node 22 broke — see "why `precommit-fix` can't
catch this" note below). It does **not** verify the `@asamuzakjp/css-color`
override or the actual resolved `node_modules` tree, so re-running the jest
suite above is still the only full confirmation after any dependency change
in this area.

**Why**: Node's native ESM `import()` handles real ESM packages fine (which
is why the many `tests/*.test.mjs` files that `import { JSDOM } from
"jsdom"` are unaffected), but Jest's CJS `require()` cannot load an ESM-only
package without Node 24.9+'s synchronous vm-module APIs. jsdom's own code
does an eager, top-level, synchronous `require()` of its dependencies, so if
any package in that chain is ESM-only, the two `review_heatmap/tests/` jest
suites crash at import time — regardless of Jest's own
`--experimental-vm-modules` flag, since the failure happens inside jsdom's
require graph, not in Jest's test-file loading.

Diagnosed 2026-07-11 (confirmed empirically by re-running the jest suite
after each change, not by reasoning about version numbers alone — an earlier
attempt at this fix pinned `^27.3.0` and declared it fixed without
re-verifying against a clean `npm ci`, and it was not: see below). Three
**independent** transitive dependencies of jsdom have each gone ESM-only in
recent releases; all three had to be pinned away simultaneously:

| Culprit                                                     | Introduced at                                                                                                                                                                                                            | Safe below                                                                                                                                                                   |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `html-encoding-sniffer` → `@exodus/bytes`                   | `jsdom@27.4.0`+ (bumps to `html-encoding-sniffer@^6`)                                                                                                                                                                    | `jsdom@27.0.0`–`27.3.0` (any keeps `html-encoding-sniffer@^4`)                                                                                                               |
| `parse5`                                                    | `jsdom@27.0.1`+ (bumps to `parse5@^8.0.0`, ESM-only)                                                                                                                                                                     | `jsdom@27.0.0` only (the sole 27.x release still on `parse5@^7.3.0`)                                                                                                         |
| `cssstyle` → `@asamuzakjp/css-color` → `@csstools/css-calc` | `@asamuzakjp/css-color@4.1.2`+ (bumps to `css-calc@^3.0.0`, ESM-only) — `cssstyle@^5.x` (required by every jsdom 27.x) always pulls in `@asamuzakjp/css-color`, so this can't be avoided by a jsdom version choice alone | forced via `package.json`'s `overrides["@asamuzakjp/css-color"] = "4.1.0"` (still depends on `@csstools/css-calc@^2.1.4`, which has a `main: dist/index.cjs` — dual CJS/ESM) |

So the fix is **both** "pin jsdom to exactly `27.0.0`" (avoids the first two)
**and** the `@asamuzakjp/css-color` override in `package.json` (avoids the
third) — pinning jsdom alone is not sufficient.

**Why `make precommit-fix SKIP=1` can't fully catch or fix this**: the
Makefile's `install` target now runs `npm ci` (added 2026-07-11 for exactly
this reason), so a fresh `make install` / `make precommit-fix` will resync
`node_modules` to whatever `package.json`/`package-lock.json` currently say —
and `check-node`'s jsdom-field guard (above) now catches the common case of
that declared version drifting. But the guard only checks the `jsdom` field
itself; it cannot know if the `@asamuzakjp/css-color` override was removed or
if `package-lock.json` resolved a bad transitive version despite a correct
`jsdom` field. Verifying the actual jsdom/css-color/parse5 versions landed
correctly still requires re-running the jest suite (above), not just
`make check-node`'s exit code, since a broken `node_modules` state fails
loudly and a merely-different-but-still-broken one can look identical from
the outside without careful diffing.

**Known behavioral gaps vs. jsdom 28+** (both still apply at 27.0.0):

- **`Blob.prototype.arrayBuffer()`** — missing in jsdom 27. Tests that need it
  should call `polyfillBlobArrayBuffer(window)` from
  `tests/helpers/jsdomPolyfills.cjs` right after creating the JSDOM instance.
- **CSSOM zero serialization** — `style.borderRadius = "0"` stays as `"0"` in
  jsdom 27 (vs. `"0px"` in 28+). Both are valid CSS; assertions should expect
  `"0"`.

**Automated dependency bumpers are a live risk to this pin** —
`.github/workflows/dependency-auto-resolver.yml` runs
`npm install undici@latest jsdom@latest` on a schedule (Monday 10 AM UTC) and
via manual dispatch, and `.github/dependabot.yml` groups minor/patch updates
for production dependencies (which includes `jsdom`). Either could open a PR
that silently reintroduces this exact breakage. As of 2026-07-11 neither has
been adjusted to respect this pin — that requires a CI/workflow-file decision
outside the scope of a docs fix; flag it to a human before merging any PR
either of them opens that touches `jsdom`, `@asamuzakjp/css-color`, `parse5`,
or `html-encoding-sniffer`.

**Upgrade path**: When the project moves to Node 24.9+ (or Jest drops the
synchronous CJS→ESM restriction), bump jsdom freely, drop the
`@asamuzakjp/css-color` override, remove the polyfill guard, and update
zero-value assertions.

## Testing browser-side scripts

Scripts like `js/graph/graph.js` execute at module top level against CDN
importmaps (`three`, GSAP) and a live DOM — they cannot be `import`ed under node.
The repo convention is a **source-level regression test**: read the file with
`fs.readFileSync`, then assert on the source (a pattern must / must not appear, a
function body must not reference an out-of-scope variable, …). Pair every
"pattern must NOT appear" assertion with a positive guard asserting what must
_stay_, so the test also catches over-deletion.

Examples: `tests/quantum_shader_scope.test.mjs` (extracts a function body and
pins a scoping bug), `tests/graph_magnetic_thumb_disabled.test.mjs` (pins the
removal of the timeline-thumb magnetic effect while guarding the slider sync).

## Testing Gotchas & Best Practices

### 1. requestAnimationFrame and Timer Leaks (Hanging Tests)

Animation loops (e.g. GSAP, Canvas/WebGL rendering loops, custom cursor loops) that schedule themselves recursively will keep Node's event loop active, causing the test runner process to hang.

- **Always track and clean up timers**: Intercept `globalThis.setTimeout` and `globalThis.requestAnimationFrame` to record the timer IDs, and explicitly clear them in `afterEach` (via `clearTimeout`).
- **Polyfill behavior**: Be aware that libraries (like `sketch.js`) might fall back to local polyfills that invoke bare `setTimeout` calls (which resolve to Node's native `globalThis.setTimeout`). Intercepting `globalThis.setTimeout` is the safest way to ensure clean test exit.

### 2. Global Navigator Mocking

Node.js has a read-only `globalThis.navigator` property. Attempting to assign `globalThis.navigator = ...` will throw a `TypeError`.

- **Use Object.defineProperty**: Mock features by defining configurable properties directly on the existing `globalThis.navigator` object (e.g. `Object.defineProperty(globalThis.navigator, "serviceWorker", { ... })`). Ensure you delete or restore the properties in `afterEach` to avoid test cross-contamination.

### 3. Dynamic Imports and Async Stubs

If your test uses a setup function (like `withCurrentScript`) to stub attributes (like `document.currentScript`) before importing a module via `await import(...)`, the setup wrapper must also be asynchronous.

- **Always await the callback**: If the wrapper cleanup runs synchronously before the dynamic import evaluates, the stubbed properties will be deleted prematurely, leading to incorrect defaults being loaded.

## Candidate ratchet (not yet implemented)

A gate test in root `tests/` asserting that every git-tracked `*.test.{js,cjs,mjs}`
lives under a directory some runner actually executes — the JS analogue of
`tests/test_makefile_test_gate.py`. Blocked on the `graph/tests` dead-test cleanup
landing first (otherwise the gate is born red).

## Testing Caveats & Gotchas

### V8 Coverage vs. Dynamic Import Query Parameters

When testing ES modules in Node, we often bypass ESM import caching by appending a unique timestamp query parameter:

```javascript
await import(`../js/ui/marquee.js?t=${Date.now()}`);
```

While this allows importing clean/fresh module states, **`c8` (V8 coverage) ignores/discards coverage mapping for URLs with query parameters**. The coverage tracker observes execution under the exact URL with the query string (e.g. `file:///.../marquee.js?t=1720518338300`), which fails to resolve directly to the local filesystem path.

- **Effect:** First-party source files loaded this way will appear as having **0% coverage** (or won't appear at all) in the coverage report.
- **Workaround:** If coverage tracking is strictly required for a module, import it once statically or dynamically without a query parameter (ensuring no test-state pollution occurs).

### Event Loop Hangs (Timer & Animation Mocking)

Node.js test runners wait for the process event loop to become completely empty before exiting. If a module sets up an animation loop (like `Sketch` or a custom `requestAnimationFrame` loop) that continuously schedules itself, the event loop will never empty.

- When mocking `requestAnimationFrame` using `setTimeout`, ensure you track all active timeout handles (e.g. in an `activeRafTimers` array) and clear them unconditionally during `afterEach`:

```javascript
let activeRafTimers = [];

beforeEach(() => {
  activeRafTimers = [];
  globalThis.requestAnimationFrame = (cb) => {
    const id = setTimeout(() => cb(100), 0);
    activeRafTimers.push(id);
    return id;
  };
  globalThis.cancelAnimationFrame = (id) => {
    clearTimeout(id);
    const idx = activeRafTimers.indexOf(id);
    if (idx !== -1) activeRafTimers.splice(idx, 1);
  };
});

afterEach(() => {
  activeRafTimers.forEach(clearTimeout);
  activeRafTimers = [];
  // restore original functions...
});
```
