## 2024-05-18 - [Centralized Debouncing]
**Learning:** Replaced ad-hoc timers and inline debouncing loops with a centralized `debounce` utility in `js/utils/debounce.js` to enhance performance during high-frequency events like window resize and scroll.
**Action:** Always utilize the central debounce utility to prevent redundant layouts and style recalculations that block the main thread.
