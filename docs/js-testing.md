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

## Candidate ratchet (not yet implemented)

A gate test in root `tests/` asserting that every git-tracked `*.test.{js,cjs,mjs}`
lives under a directory some runner actually executes — the JS analogue of
`tests/test_makefile_test_gate.py`. Blocked on the `graph/tests` dead-test cleanup
landing first (otherwise the gate is born red).
