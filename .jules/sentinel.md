## 2024-05-28 - Fix stored XSS via JSON config rendering

**Vulnerability:** User-controlled configuration parameters (like ticker names and scenario descriptions) were directly injected into DOM via `innerHTML` without sanitization.
**Learning:** Even statically hosted or internal data rendering tools are vulnerable to XSS if they display names/labels sourced from mutable JSON files dynamically.
**Prevention:** Always wrap dynamically interpolated values in DOM element strings with an `escapeHtml` utility before appending them via `innerHTML`.
