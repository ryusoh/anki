# Security Learnings

## 2024-05-28 - Fix stored XSS via JSON config rendering

**Vulnerability:** User-controlled configuration parameters (like ticker names and scenario descriptions) were directly injected into DOM via `innerHTML` without sanitization.
**Learning:** Even statically hosted or internal data rendering tools are vulnerable to XSS if they display names/labels sourced from mutable JSON files dynamically.
**Prevention:** Always wrap dynamically interpolated values in DOM element strings with an `escapeHtml` utility before appending them via `innerHTML`.

## 2023-10-27 - DOM-Based XSS in Error Handling

**Vulnerability:** Found `error.message` being directly interpolated into `innerHTML` in the calendar page (`js/pages/calendar/index.js`), creating a DOM-based XSS risk if the error message is attacker-controlled.
Example:

```javascript
element.innerHTML = `<p>${error.message}</p>`;
```

**Learning:** Even internal error objects should be treated as potentially unsafe input. Assigning variables to `innerHTML` without sanitization is a recurrent pattern in vanilla JS development that bypasses modern framework protections.
**Prevention:** When dynamically rendering text content inside an element, use safe DOM methods like `document.createElement()` and `element.textContent = value` instead of template strings assigned to `innerHTML`. If `innerHTML` must be used, always run the input through a sanitization function like `escapeHtml`.

## 2024-03-14 - Prevent DOM-based XSS when interpolating Anki Deck Names

**Vulnerability:** Dynamic strings like `deckName` derived from Anki's stats endpoint were being injected directly into the DOM using `innerHTML` to build custom Chart.js legends.
**Learning:** Even though the data is generated internally by the add-on/Anki backend, user-supplied names (like Anki deck names) can contain HTML or script tags. When rendered in the webview via `innerHTML` without sanitization, this exposes the application to DOM-based Cross-Site Scripting (XSS).
**Prevention:** Always wrap dynamically injected text values derived from Anki properties with an HTML escaping utility (like `escapeHtml`) before concatenating them into `innerHTML` strings.

## 2024-05-30 - Prevent DOM-based XSS when interpolating crosshair entry properties in terminal UI

**Vulnerability:** Dynamic properties like `entry.label`, `entry.color`, `entry.deltaFormatted`, and `entry.percentFormatted` were being directly injected into the DOM using `innerHTML` to build custom terminal crosshair ranges.
**Learning:** Even though the terminal UI processes internal formatted data, the labels and colors could still originate from external data sources (e.g. ticker symbols). If a user can inject malicious payload as the ticker name, it will be executed when rendered.
**Prevention:** Always wrap dynamically injected text values or color properties with an HTML escaping utility (like `escapeHtml`) before concatenating them into `innerHTML` strings.

## 2026-03-21 - Refactored silent catch blocks to prevent generic error suppression

**Vulnerability:** Empty catch blocks were indiscriminately swallowing all exceptions during `fetch` and network requests, rendering debugging impossible and hiding true failure modes across data loaders.
**Learning:** Suppressing exceptions indiscriminately without logging conceals application instability from developers and creates confusing silent failures for end users.
**Prevention:** Always log exceptions or explicitly document via code comments why an error is deliberately being ignored inside a catch block to enforce resilient application behaviour.

## 2024-03-20 - Prevent DOM-based XSS in terminal crosshair and chart legends

**Vulnerability:** Dynamic properties like `color` in chart legends and date labels (`startLabel`, `endLabel`, `durationLabel`) in terminal UI were interpolated directly into the DOM using `innerHTML` without sanitization.
**Learning:** Even internal formatting values or properties like colors derived from backend configurations could potentially be manipulated.
**Prevention:** Always wrap dynamically injected text values or color properties with an HTML escaping utility (like `escapeHtml`) before concatenating them into `innerHTML` strings.

## 2024-03-21 - Flawed gitignore auditing

**Vulnerability:** A security audit script (`tools/security_audit.py`) was generating false positives by checking `git check-ignore <dir>/` on a directory that legitimately contained a tracked file (`hash_map.json`), masking potential real issues and causing developer fatigue.
**Learning:** `git check-ignore` on a directory path returns a non-zero exit code if the directory contains tracked files, even if the `.gitignore` rules correctly ignore all other untracked contents in that directory.
**Prevention:** When writing custom security scripts to verify gitignore coverage of a directory that might contain tracked files, test the ignore rules against a dummy file path (e.g., `<dir>/test_dummy.json`) rather than the directory itself.

## 2026-03-24 - Fix silent exceptions in optional UI initializers

**Vulnerability:** Empty catch blocks were swallowing all exceptions during the initialization of optional UI components (glass effect and stats customizer) in `tabbed_stats/__init__.py`. This suppresses errors, making debugging impossible and hiding failures.
**Learning:** Suppressing exceptions indiscriminately without logging conceals application instability from developers and creates confusing silent failures for end users. Even for optional components where a fallback to standard UI is desired, the failure must be logged.
**Prevention:** Always log exceptions (e.g., using `print(..., file=sys.stderr)`) or explicitly document via code comments why an error is deliberately being ignored inside a catch block to enforce resilient application behaviour.

## 2024-05-31 - Refactored silent catch blocks to prevent generic error suppression in UI layers

**Vulnerability:** Empty catch blocks were intentionally silencing all exceptions (with `/* no-op */` comments or silent fallbacks) during initialization of optional UI components like `js/ui/reduced_motion.js`, `js/ui/service_worker_register.js`, and data fetching in `js/transactions/terminalStats.js`. This suppresses errors, hiding failures and potential instability.
**Learning:** Suppressing exceptions indiscriminately without logging conceals application instability from developers and creates confusing silent failures for end users. Even for optional components where a fallback is desired, the failure must be logged.
**Prevention:** Always log exceptions (e.g., using `console.warn(..., error)`) to ensure resilient application behavior and debugging capabilities.

## 2024-03-26 - Fix nested HTML tag bypass in regex sanitization

**Vulnerability:** A regex-based HTML tag stripper in `js/graph/viz_utils.js` was using consecutive `replace` calls, leaving it vulnerable to nested tag bypasses like `<<script>script>`.
**Learning:** Sequential `.replace()` calls without a loop are insufficient for sanitization because removing the inner tag can accidentally form a new valid tag from the surrounding characters.
**Prevention:** To prevent nested HTML tag bypasses in regex-based sanitization routines, apply the replacement inside a `do...while` loop until the string stops changing.

## 2026-03-29 - Prevent DOM-based XSS when interpolating error messages in graph loader

**Vulnerability:** In `js/graph/graph.js`, the error message from a failed fetch call (`e.message`) was interpolated directly into the DOM using `innerHTML` without sanitization.
**Learning:** Raw error messages, even those generated by internal fetch requests or logic, could potentially contain unescaped HTML characters. If a user can trigger an error with a malicious payload, it will be executed when rendered.
**Prevention:** Always wrap dynamically injected text values such as error messages with an HTML escaping utility (like `escapeHtml`) before concatenating them into `innerHTML` strings.

## 2024-05-31 - Prevent DOM-based XSS when interpolating user-controlled options in HTML UIs

**Vulnerability:** In `awesome_tts/awesometts/gui/homescreen.py`, user-controlled preset names were directly interpolated into an HTML string for a `<select>` dropdown without escaping, creating a DOM-based XSS risk if the user creates a preset name containing malicious tags.
**Learning:** Whenever generating HTML strings inside Python (or any backend) to be injected into a WebView (like Anki's deck browser content), any user-controlled input (such as profile configurations or preset names) must be escaped, even if the backend feels "safe".
**Prevention:** Use Python's `html.escape(variable, quote=True)` when interpolating strings into HTML templates, especially when inserting inside attribute values or text content.

## 2026-03-31 - Prevent DOM-based XSS when interpolating input in terminal commands

**Vulnerability:** User-controlled configuration parameters (like terminal inputs) were directly injected into DOM via `insertAdjacentHTML` despite having an `escapeHtml` call.
**Learning:** It is always safer to use `document.createElement()` and `element.textContent` over `insertAdjacentHTML` or `innerHTML`.
**Prevention:** When dynamically rendering text content inside an element, use safe DOM methods like `document.createElement()` and `element.textContent = value` instead of template strings assigned to `insertAdjacentHTML`.

## 2026-04-02 - Fix SQL Injection in Config Schema Updates

**Vulnerability:** Unsanitized string interpolation (`%s`) was used to insert variable table and column names directly into SQLite commands like `PRAGMA table_info`, `ALTER TABLE`, and `UPDATE` in `awesome_tts/awesometts/config.py`.
**Learning:** SQLite parameterization (`?`) only works for values, not for identifiers like table or column names. Using `%s` for identifiers leaves the application vulnerable to SQL injection if those names originate from untrusted sources.
**Prevention:** Always quote identifiers by wrapping them in double quotes (`"`) and escaping any internal double quotes with `.replace('"', '""')` before using string interpolation to safely construct dynamic schema modifications.

## 2025-04-10 - CRITICAL: Fix exec() vulnerability in awesome_tts

**Vulnerability:** Found `exec()` being used in `awesome_tts/awesometts/languagetools.py` to evaluate base64-encoded strings imported from an obfuscated `trial.py` module.
**Learning:** This obfuscated approach was used for loading `py-machineid` logic to fingerprint hosts securely, but utilizing `exec()` introduces significant remote code execution (RCE) and code injection risks, while heavily diminishing code readability and audibility.
**Prevention:** Avoid `exec()` unconditionally. Replace such obfuscation layers with directly imported code. In this case, I created a safe, de-obfuscated `machineid.py` and computed the HMAC directly to remove all base64+exec vulnerabilities.

## 2024-05-31 - Prevent DOM-based XSS by removing `innerHTML` in chart cleanup and terminal reset

**Vulnerability:** Emptying DOM elements using `element.innerHTML = ""` in `js/terminal.js` and `js/commands/handler.js` to clear output.
**Learning:** While assigning an empty string to `innerHTML` is not actively exploitable as an XSS vector itself, retaining `.innerHTML` setters in the codebase violates strict defense-in-depth secure coding standards. It trains developers to reach for unsafe DOM manipulation APIs, keeps the codebase non-compliant with modern SAST linters (like `no-inner-html`), and risks accidental introduction of XSS if the string assignment is later modified to include untrusted variables.
**Prevention:** Always use safe DOM APIs like `element.textContent = ""` or `element.replaceChildren()` when clearing element contents to maintain robust defense-in-depth and avoid security regressions.

## 2026-04-16 - Prevent command injection by replacing shell=True with native Python pipelines

**Vulnerability:** The `subprocess.run` call inside `__exec__` in `awesome_tts/awesometts/machineid.py` used `shell=True` with string arguments containing pipes, introducing a command injection risk.
**Learning:** Shell pipelines (like `| awk` or `| cut`) can be entirely replaced by lightweight native Python string manipulations and regexes. Additionally, migrating away from `shell=True` changes the exception raised when a command is missing: instead of the shell successfully exiting with a non-zero code (triggering `subprocess.SubprocessError` when `check=True`), Python raises an `OSError` (`FileNotFoundError`).
**Prevention:** Avoid `shell=True` in `subprocess.run` unconditionally. Pass commands as lists, replace shell pipelines with native Python parsing of the raw `subprocess.stdout`, and always catch `OSError` alongside `subprocess.SubprocessError` to preserve graceful fallbacks.

## 2024-06-11 - Prevent DOM-based XSS by removing `innerHTML` in graph data error handler

**Vulnerability:** Emptying DOM elements using `loading.innerHTML = ...` in `js/graph/graph.js` to render graph fetch error messages, which injects `e.message` into the DOM.
**Learning:** Even internal error objects should be treated as potentially unsafe input. Assigning variables to `innerHTML` without sanitization is a recurrent pattern in vanilla JS development that bypasses modern framework protections.
**Prevention:** When dynamically rendering text content inside an element, use safe DOM methods like `document.createElement()` and `element.textContent = value` instead of template strings assigned to `innerHTML`.

## 2026-04-21 - Prevent DOM-based XSS by removing innerHTML in lab analysis page

**Vulnerability:** Emptying DOM elements or appending static HTML with `innerHTML` in `js/pages/analysis/lab.js`.
**Learning:** While assigning static strings to `innerHTML` isn't an active XSS vector, retaining it violates strict defense-in-depth secure coding standards. It trains developers to use unsafe DOM APIs, keeps the codebase non-compliant with modern SAST linters, and risks accidental introduction of XSS.
**Prevention:** Always use safe DOM APIs like `element.textContent = ""` or `document.createElement()` to maintain robust defense-in-depth and avoid security regressions.

## 2026-05-02 - Add timeout to prevent Denial of Service on external API request

**Vulnerability:** A `requests.post` call to the ElevenLabs API in `awesome_tts/awesometts/service/elevenlabs.py` lacked a `timeout` parameter, allowing the application thread to hang indefinitely if the API server failed to respond.
**Learning:** Network calls to external APIs without explicit timeouts introduce Denial of Service (DoS) and application hang risks.
**Prevention:** Always include a `timeout` parameter (e.g., `timeout=10`) when using the `requests` library to interact with external services.

## 2026-04-30 - Prevent DOM-based XSS by removing innerHTML in graph data error handler

**Vulnerability:** Emptying DOM elements using `loading.innerHTML = ...` in `js/graph/graph.js` to render graph fetch error messages, which injects `e.message` into the DOM.
**Learning:** Even internal error objects should be treated as potentially unsafe input. Assigning variables to `innerHTML` without sanitization is a recurrent pattern in vanilla JS development that bypasses modern framework protections.
**Prevention:** When dynamically rendering text content inside an element, use safe DOM methods like `document.createElement()` and `element.textContent = value` instead of template strings assigned to `innerHTML`.

## 2024-05-01 - [Missing Timeout Parameter in requests]

**Vulnerability:** Several API integrations using Python's `requests` library lacked a `timeout` parameter.
**Learning:** External network calls without explicit timeouts can cause the application thread to hang indefinitely, resulting in DoS vulnerabilities or unresponsive applications when the external service is slow or unresponsive.
**Prevention:** Always include a `timeout` parameter (e.g., `timeout=10`) wrapped within a `try...except requests.exceptions.RequestException` block when using the `requests` library to interact with external services.

## 2026-05-04 - Prevent DOM-based XSS by replacing `innerHTML` in chart legends with native DOM APIs

**Vulnerability:** In `js/commands/retention.js`, `js/commands/due.js`, and `js/commands/reviews.js`, dynamic chart legends (including `deckName` strings and colors) were constructed via string accumulation and injected directly into the DOM using `legend.innerHTML = ...`.
**Learning:** While some dynamic properties may seem harmless or appear properly escaped within template strings, assigning strings directly to `.innerHTML` in application logic violates strict defense-in-depth secure coding standards. It trains developers to reach for unsafe DOM manipulation APIs, keeps the codebase non-compliant with modern SAST linters (like `no-inner-html`), and creates brittle points where future modifications could accidentally bypass escaping and introduce DOM-based Cross-Site Scripting (XSS). Custom testing mocks will also need updates to support native APIs if they were originally designed around reading `.innerHTML`.
**Prevention:** Always use safe DOM APIs like `document.createElement()`, `document.createTextNode()`, and `element.appendChild()` to dynamically construct UI elements rather than assigning HTML strings to `.innerHTML`. When clearing elements, use `element.textContent = ""` or `element.replaceChildren()`.
