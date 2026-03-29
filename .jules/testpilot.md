## 2024-03-28 - Testing JS Chart UIs

**Learning:** When testing Chart.js or GSAP UI logic in a headless Node environment without JSDOM, it is essential to mock `global.document` with dummy elements that have simple mock objects representing `classList`, `style`, and `getContext()`. Similarly, `window.Chart` must be stubbed with a class implementation that has the same signature.
**Prevention:** Avoid rewriting the entire testing environment just for UI functions, and instead use the lightweight global mock pattern already used in `tests/handler_regression.test.mjs`. Use `global.window` and `global.document` initialized BEFORE any dynamic imports using `await import()`.

## 2024-03-31 - Proper Import Testing

**Learning:** Never copy-paste core application functions into test files to mock or simplify testing. Doing so provides 0% coverage to the actual application code and results in false confidence.
**Prevention:** Tests must import and execute the actual module functions (e.g., dynamically via `await import()`) to provide valid coverage and accurately verify module behavior.

## 2024-03-31 - Asserting Side Effects

**Learning:** When unit testing UI or DOM-manipulating functions, explicitly assert the resulting DOM side-effects (such as `classList` modifications or `textContent` changes) and return values.
**Prevention:** Merely executing code to hit coverage lines without asserting output or state violates testing standards.
