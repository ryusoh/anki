## 2024-05-28 - Fix stored XSS via JSON config rendering

**Vulnerability:** User-controlled configuration parameters (like ticker names and scenario descriptions) were directly injected into DOM via `innerHTML` without sanitization.
**Learning:** Even statically hosted or internal data rendering tools are vulnerable to XSS if they display names/labels sourced from mutable JSON files dynamically.
**Prevention:** Always wrap dynamically interpolated values in DOM element strings with an `escapeHtml` utility before appending them via `innerHTML`.

## 2023-10-27 - DOM-Based XSS in Error Handling

**Vulnerability:** Found `error.message` being directly interpolated into `innerHTML` (`element.innerHTML = \`<p>\${error.message}</p>\``) in the calendar page (`js/pages/calendar/index.js`), creating a DOM-based XSS risk if the error message is attacker-controlled.
**Learning:** Even internal error objects should be treated as potentially unsafe input. Assigning variables to `innerHTML`without sanitization is a recurrent pattern in vanilla JS development that bypasses modern framework protections.
**Prevention:** When dynamically rendering text content inside an element, use safe DOM methods like`document.createElement()`and`element.textContent = value`instead of template strings assigned to`innerHTML`. If `innerHTML`must be used, always run the input through a sanitization function like`escapeHtml`.
