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

**Learning:** When asserting tolerance or specific behaviors of custom JS formatters (like `formatCurrencyCompact`), branch coverage relies heavily on testing decimals exactly over/under rounding thresholds alongside edge cases like missing DOM nodes (e.g. testing returning null).
**Action:** Use specific numerical boundary inputs (e.g. `15_000_000.08`) rather than just random values to hit internal thresholds and reliably assert specific decimal precision paths.

## 2026-05-11 - Zoom toggle edge cases and JS formatting tolerances

**Learning:** When asserting tolerance or specific behaviors of custom JS formatters (like formatCurrencyCompact), branch coverage relies heavily on testing decimals exactly over/under rounding thresholds alongside edge cases like missing DOM nodes.
**Action:** Use specific numerical boundary inputs (e.g., 15_000_000.08) rather than just random values to hit internal thresholds and reliably assert specific decimal precision paths.

## 2024-05-24 - Test Python tooling scripts

**Learning:** Testing standalone scripts that interact heavily with the filesystem and use simple logic patterns (like `security_check.py` or `export_for_git.py`) requires thorough use of Pytest's `monkeypatch` and `tempfile.TemporaryDirectory`. When testing modules with side-effects upon import, mock dependencies _before_ executing the module using `importlib.util.spec_from_file_location`.

**Action:** Ensure temporary files are cleaned up using `tempfile`, and strategically patch functions like `subprocess.run` and built-ins like `sys.stderr` to prevent tests from bleeding side-effects.

## 2024-05-13 - Added Tests for hide_deck_collapse, unify_review_count_colors, and rewrite_text_of_study_cards

**Learning:** Anki `aqt` UI classes such as `DeckBrowser` or `Overview` must be mocked fully at the module scope level inside `conftest.py` (including setting `builtins.DeckBrowser` if code expects class instantiation without module prefixes) to successfully run python unit tests targeting UI code.
**Action:** When creating tests for untested UI logic that rely on complex external dependencies (`aqt`), always update `conftest.py` with the complete path tree of required modules (`aqt.deckbrowser`, `aqt.overview`) and ensure `builtins` are appropriately patched to pass module loading.

## 2024-05-15 - Improve test coverage for tools/security_audit.py

**Learning:** When generating test coverage for a Python script using `subprocess` from another test or running `sys.exit()`, the normal coverage tracking might not pick it up correctly unless you invoke the functions explicitly inside the tests or configure `coverage` to track subprocesses. Also, mocking builtins like `open` can cause issues if not done correctly, and you must pass all arguments as required by the mocked functions.
**Action:** Wrote exhaustive unit tests explicitly calling the functions in `tools/security_audit.py` to drive coverage to >99%, avoiding using `subprocess` where we could just call the function directly and patching internal implementations (like `sys.exit`) for testability.

## 2025-02-14 - Isolate DOM Globals for Node.js ES Modules Tests

**Learning:** When testing ES modules in Node.js that require DOM-like environments (like `transactionState` checking `document.querySelector`), the globals (`global.window`, `global.document`) must be mocked **before** dynamically importing the module with `await import(...)`. Failing to do so causes ReferenceErrors during module initialization.
**Action:** Use setup blocks in test suites to instantiate mock `global.window` and `global.document` objects before importing the target files, and remember to clean them up afterward.

## 2025-05-20 - Reference Testing Adjustments

**Learning:** Found an error where test validations were backwards for `find_references()` edge direction.
**Action:** When evaluating `find_references` output, ensure that tests assert `target` is the referenced card (the pattern owner) and `source` is the text owner (the card doing the referencing).

## 2025-05-20 - Subprocess and Test Coverage

**Learning:** Found an issue where the `security_audit.py` was being run using `subprocess` with mocked builtins in a test that couldn't properly apply or clear the mock in `test_tools_coverage.py`, which failed actual `python3 tools/security_audit.py` checks as it left dummy API keys in test code that the audit checked itself.
**Action:** When testing scripts like `security_audit.py`, explicitly call the functions in the test file instead of using `subprocess.run()`. This also improves test coverage and avoids leaking mock data into tracked files that the audit script is scanning.

## 2025-05-20 - Testing Top Level Execution Logic

**Learning:** Found an issue where the main execution logic in `graph/quick_3d.py` was being executed immediately on import because it wasn't behind an `if __name__ == '__main__':` block. This caused unit tests importing functions from it to crash when files didn't exist or global state was altered.
**Action:** Move main execution logic behind an `if __name__ == '__main__':` block to ensure testability of functions within the module. Use exceptions to catch `FileNotFoundError` gracefully for dependencies.

## 2025-10-23 - Python Graph Analysis Testing Pattern

**Learning:** When testing Python graph analysis utilities that use NetworkX (e.g., `get_hub_nodes` or `get_top_nodes`), instantiate minimal synthetic `nx.DiGraph` objects and directly inject expected node attributes (e.g., `G.add_node('id', pagerank=0.05)`) instead of executing the entire graph building pipeline.
**Action:** This practice strictly isolates specific analysis logic and ensures reliable boundary testing.

## 2026-05-25 - Unit test coverage improvements

**Learning:** When using `unittest.mock.patch` in Python to mock file operations, always patch `builtins.open` instead of trying to patch `open` on the target module directly (e.g., `@patch('module.open')`), as the latter will raise an AttributeError if `open` was not explicitly imported in that module.
**Action:** Remember to use `@patch('builtins.open')` across the board to ensure consistent, stable mocking behavior without needing the target module to explicitly import the built-in.

## 2024-05-26 - Increased unit test coverage in `graph` modules

**Action:** Added tests for edge cases and CLI argument parsing branches in `graph/builder.py`, `graph/incremental_export.py`, and `graph/watch_and_update.py`.
**Learning:** Found an existing bug where `get_top_nodes` was calling `compute_pagerank` instead of `_compute_pagerank`, which would raise a NameError.
**Learning:** Mocking module executions directly via `runpy.run_module(..., run_name="__main__")` properly checks if `main()` was invoked from `if __name__ == '__main__':` while isolating variables and tracking statement coverage appropriately. Used `unittest.mock.patch('sys.exit')` to avoid terminating test runners during execution.

## 2026-05-31 - Graph Analysis Output Tests

**Learning:** When testing formatting and output functions that use `print` (such as `compare_decks` and `print_hub_notes`), use pytest's `capsys` fixture to capture `stdout` and assert on substring presence rather than exact string matching. This prevents brittle tests that fail on minor whitespace or truncation logic changes.
**Action:** Use `capsys.readouterr().out` and `assert 'substring' in out` for CLI output tests.

## 2024-05-31 - Generating Test Coverage Reports for Python

**Learning:** To correctly generate Python test coverage reports for specific modules (e.g., `graph`) using `pytest-cov`, the root directory must be properly added to the Python path.
**Action:** Use `PYTHONPATH=. python3 -m pytest --cov=<module_name> --cov-report=term-missing` directly from the repository root to ensure correct path resolution and accurate coverage metrics.

## 2024-06-03 - Resolving Unreachable UI Branch Coverages

**Learning:** Certain UI branches like invalid state edge cases on deeply nested fallback functions or early-returns mapping DOM state checks cannot be safely hit without removing defensive lines. Testing requires robust mock generation of complex configurations (e.g., overriding `.getElementById` globally to catch specific elements while leaving others untouched).
**Action:** Replicate full browser configurations, explicitly clear overrides via global mocking, and accept small percentages of defensive coverage loss (e.g. `c8 ignore next`) over restructuring logic.

## 2024-06-04 - Safely Restoring Global Mocks inside Tests

**Learning:** When running multiple sequential tests using a `node:test` framework, mutating global DOM or Chart mocks (e.g. `global.window.Chart`) and failing to wrap the test execution explicitly with `try...finally` cleanup blocks can permanently poison the environment. A thrown error within a test causes the runner to bypass downstream restoration assignments (`global.window.Chart = original`), leading to cascaded `"Chart render error"` failures in subsequent suites.
**Action:** Always wrap `Act` and `Assert` steps that depend on mocked global states inside `try` blocks and place the teardown inside a `finally` block to guarantee environment restoration, even if an assertion unexpectedly fails.

## 2026-06-05 - Test tools and regex extraction logic

**Learning:** When using `runpy.run_module` to execute a script's `__main__` block, ensure that if the original script's logic invokes `sys.exit()` natively, that behavior is accurately modeled and tested. Use a simple structure of `sys.exit(main())` within `if __name__ == '__main__':` and assert that `main()` is correctly called. When parsing search queries and ignoring negations or logical operators using a regex, it is more reliable to assert exact logical parts output in list comprehensions and match `re.finditer` components than trusting loose string matching.
**Action:** When creating tests for parsing search terms (like in `prioritize_front_field_search/search.py`), clearly assert `extract_terms` behaves properly with quoted strings and negations by comparing against a static target list.
