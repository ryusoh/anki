1. **Optimize `onPointerMove` in `js/ambient/quantum_shader.js`**: Use `requestAnimationFrame` + a boolean lock (`ticking`) for the high-frequency `pointermove` event handler to prevent layout thrashing and throttle the updates to the screen refresh rate, matching the proven pattern in this repo (e.g. `js/ui/tableGlassEffect.js`).

2. **Verify changes**: Make sure the behaviour is unchanged and `make precommit SKIP=1` stays green. Use `node` to test a microbenchmark comparing the unthrottled loop and throttled lock loop.

3. **Complete pre-commit steps**: `SKIP_FETCH=1 make precommit SKIP=1` to ensure proper testing, verification, review, and reflection are done.

4. **Submit PR**: Open a PR with the performance improvements.
