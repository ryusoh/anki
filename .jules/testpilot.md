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

## 2024-05-30 - Module-level State Fallback Paths

**Learning:** To test module-level state fallback paths, direct variable assignment via module exports (if available) or recreating conditions where state is null/undefined is sometimes necessary to trigger default returns when testing pure functions interacting with that state.
**Action:** Use temporary state modification and `finally` blocks to restore state, or directly set state to null to test fallback paths.

## 2025-02-28 - Add coverage tests for config.js, assetClasses.js, and host.js

**Learning:** Adding test coverage for basic configuration and utilities that are often skipped.
**Action:** Created missing tests to reach 100% test coverage for js/config.js, js/config/assetClasses.js, and js/utils/host.js.

## 2025-04-27 - DOM Mocking for Tests

**Learning:** We need to provide minimal mocked versions of browser globals (like `window` and `document`) BEFORE importing JS modules that access them during their top-level evaluation.
**Action:** Always inject required DOM mock dependencies into the `global` object before using dynamic `await import()` on frontend modules under test in our Node test runner.
**Learning:** Adding test coverage for basic configuration and utilities that are often skipped.
**Action:** Created missing tests to reach 100% test coverage for js/config.js, js/config/assetClasses.js, and js/utils/host.js.

## 2024-05-10 - Three missing test coverage a day

**Learning:** Added test coverage for missing logic paths in `data/anki/generate_custom_stats.py` and `js/transactions/utils.js`. Found that testing the `__main__` entry block of a python script via `runpy` can be problematic if the file has side-effects (like sys.exit or sqlite queries without proper mocks) or is not cleanly isolatable, and can be considered a "fake coverage" antipattern if exceptions are just swallowed.
**Action:** Focus on testing actual modular functions. I've added tests for formatCurrencyCompact missing coverage in `tests/utils.test.mjs` and `tests/utils_tx.test.mjs`, and tests for missing SQLite fallback and missing files in `data/anki/tests/test_generate_custom_stats.py`.

## 2026-05-11 - Zoom toggle edge cases & JS formatting tolerances

**Learning:** When asserting tolerance or specific behaviors of custom JS formatters (like `formatCurrencyCompact`), branch coverage relies heavily on testing decimals exactly over/under rounding thresholds alongside edge cases like missing DOM nodes (e.g. testing  returning null).
**Action:** Use specific numerical boundary inputs (e.g. `15_000_000.08`) rather than just random values to hit internal thresholds and reliably assert specific decimal precision paths.

## 2026-05-11 - Zoom toggle edge cases and JS formatting tolerances

**Learning:** When asserting tolerance or specific behaviors of custom JS formatters (like formatCurrencyCompact), branch coverage relies heavily on testing decimals exactly over/under rounding thresholds alongside edge cases like missing DOM nodes.
**Action:** Use specific numerical boundary inputs (e.g., 15_000_000.08) rather than just random values to hit internal thresholds and reliably assert specific decimal precision paths.

## 2024-05-24 - Test Python tooling scripts

**Learning:** Testing standalone scripts that interact heavily with the filesystem and use simple logic patterns (like `security_check.py` or `export_for_git.py`) requires thorough use of Pytest's `monkeypatch` and `tempfile.TemporaryDirectory`. When testing modules with side-effects upon import, mock dependencies *before* executing the module using `importlib.util.spec_from_file_location`.

**Action:** Ensure temporary files are cleaned up using `tempfile`, and strategically patch functions like `subprocess.run` and built-ins like `sys.stderr` to prevent tests from bleeding side-effects.

## 2024-05-13 - Added Tests for hide_deck_collapse, unify_review_count_colors, and rewrite_text_of_study_cards
**Learning:** Anki `aqt` UI classes such as `DeckBrowser` or `Overview` must be mocked fully at the module scope level inside `conftest.py` (including setting `builtins.DeckBrowser` if code expects class instantiation without module prefixes) to successfully run python unit tests targeting UI code.
**Action:** When creating tests for untested UI logic that rely on complex external dependencies (`aqt`), always update `conftest.py` with the complete path tree of required modules (`aqt.deckbrowser`, `aqt.overview`) and ensure `builtins` are appropriately patched to pass module loading.
