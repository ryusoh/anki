## 2024-03-14 - Flaky async test prevention

**Learning:** Raw NodeJS setTimeout based debounce testing requires sufficiently wide timer cushions since the NodeJS event loop might fire closely timed actions out of order due to GC pauses or generic CPU context switches in CI environments.
**Action:** Always buffer small async wait test times (e.g. going from 10ms wait / 15ms assert to 50ms wait / 100ms assert).

## 2024-03-24 - Node.js ESM Aliases and Coverage Tracking
**Learning:** Testing ESM files using the `@js/` path alias is problematic in Node.js without specific loaders. Node `assert` tests natively fail or bypass alias resolution.
**Action:** Focus on utilities with minimal dependency trees (e.g. `js/utils/formatting.js`, `js/utils/logger.js`, `js/utils/smoothing.js`). Use `npx c8 node tests/filename.test.js` to see coverage gaps per file before attempting PRs.
