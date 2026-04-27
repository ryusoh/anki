## 2024-03-28 - Testing JS Chart UIs

**Learning:** When testing Chart.js or GSAP UI logic in a headless Node environment without JSDOM, it is essential to mock `global.document` with dummy elements that have simple mock objects representing `classList`, `style`, and `getContext()`. Similarly, `window.Chart` must be stubbed with a class implementation that has the same signature.
**Prevention:** Avoid rewriting the entire testing environment just for UI functions, and instead use the lightweight global mock pattern already used in `tests/handler_regression.test.mjs`. Use `global.window` and `global.document` initialized BEFORE any dynamic imports using `await import()`.

## 2024-03-31 - Proper Import Testing

**Learning:** Never copy-paste core application functions into test files to mock or simplify testing. Doing so provides 0% coverage to the actual application code and results in false confidence.
**Prevention:** Tests must import and execute the actual module functions (e.g., dynamically via `await import()`) to provide valid coverage and accurately verify module behavior.

## 2024-03-31 - Asserting Side Effects

**Learning:** When unit testing UI or DOM-manipulating functions, explicitly assert the resulting DOM side-effects (such as `classList` modifications or `textContent` changes) and return values.
**Prevention:** Merely executing code to hit coverage lines without asserting output or state violates testing standards.

## 2024-05-18 - handleCommand fallback and Reviews Data edge cases

**Learning:** `handleCommand` correctly drops unhandled or partially matched commands by returning `{ handled: false }` rather than throwing or auto-suggesting if the prefix doesn't definitively map to a valid end state. Test coverage must ensure it falls through.
**Action:** When testing partial commands, check for `handled: false`.
**Learning:** `getReviewStatsData` calculates a `preSliceSum` object internally when `byDeck` is false, which accumulates historic time metrics needed for accurate rendering.
**Action:** Ensure that mock data injected into `global.window.reviewStatsData` has sufficient prior history items before the sliced time window to trigger `preSliceSum` logic.

## 2024-05-18 - Node.js JSDOM Testing Edge Cases

**Learning:** `jsdom` testing dependencies can easily fail in fresh environments when module paths don't match, particularly if tests attempt to import files needing missing packages. Modifying `package.json` to resolve test failures is strictly forbidden by repository boundaries unless specifically tasked.
**Prevention:** If testing `JSDOM` UI tests fail due to missing dependencies, restore the original state and avoid artificially fixing CI dependencies. Focus purely on writing missing code coverage via native unit tests rather than attempting to fix unrelated repository failures.

## 2024-05-18 - Node.js Custom Runner and Missing Globals

**Learning:** When using the custom Node.js runner to test modules that eventually import `config.js` (which accesses `document.querySelector`), the tests will crash with `ReferenceError: document is not defined`.
**Prevention:** Always provide a lightweight stub for `global.window` and `global.document` (e.g. `global.window = { matchMedia: () => ({ matches: false }) }; global.document = { querySelector: () => null, createElement: () => ({}), head: { appendChild: () => {} } };`) _before_ executing the dynamic `await import()` of the target module.

## 2025-04-27 - DOM Mocking for Tests

**Learning:** We need to provide minimal mocked versions of browser globals (like `window` and `document`) BEFORE importing JS modules that access them during their top-level evaluation.
**Action:** Always inject required DOM mock dependencies into the `global` object before using dynamic `await import()` on frontend modules under test in our Node test runner.
