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

## 2024-03-26 - Fix nested HTML tag bypass in regex sanitization

**Vulnerability:** A regex-based HTML tag stripper in `js/graph/viz_utils.js` was using consecutive `replace` calls, leaving it vulnerable to nested tag bypasses like `<<script>script>`.
**Learning:** Sequential `.replace()` calls without a loop are insufficient for sanitization because removing the inner tag can accidentally form a new valid tag from the surrounding characters.
**Prevention:** To prevent nested HTML tag bypasses in regex-based sanitization routines, apply the replacement inside a `do...while` loop until the string stops changing.

## 2026-03-29 - Prevent DOM-based XSS when interpolating error messages in graph loader

**Vulnerability:** In `js/graph/graph.js`, the error message from a failed fetch call (`e.message`) was interpolated directly into the DOM using `innerHTML` without sanitization.
**Learning:** Raw error messages, even those generated by internal fetch requests or logic, could potentially contain unescaped HTML characters. If a user can trigger an error with a malicious payload, it will be executed when rendered.
**Prevention:** Always wrap dynamically injected text values such as error messages with an HTML escaping utility (like `escapeHtml`) before concatenating them into `innerHTML` strings.

## 2026-03-31 - Prevent DOM-based XSS when interpolating input in terminal commands

**Vulnerability:** User-controlled configuration parameters (like terminal inputs) were directly injected into DOM via `insertAdjacentHTML` despite having an `escapeHtml` call.
**Learning:** It is always safer to use `document.createElement()` and `element.textContent` over `insertAdjacentHTML` or `innerHTML`.
**Prevention:** When dynamically rendering text content inside an element, use safe DOM methods like `document.createElement()` and `element.textContent = value` instead of template strings assigned to `insertAdjacentHTML`.
## $(date +%Y-%m-%d) - Fix SQL Injection in Config Schema Updates
**Vulnerability:** Unsanitized string interpolation (`%s`) was used to insert variable table and column names directly into SQLite commands like `PRAGMA table_info`, `ALTER TABLE`, and `UPDATE` in `awesome_tts/awesometts/config.py`.
**Learning:** SQLite parameterization (`?`) only works for values, not for identifiers like table or column names. Using `%s` for identifiers leaves the application vulnerable to SQL injection if those names originate from untrusted sources.
**Prevention:** Always quote identifiers by wrapping them in double quotes (`"`) and escaping any internal double quotes with `.replace('"', '""')` before using string interpolation to safely construct dynamic schema modifications.
