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
