## 2024-05-18 - [Centralized Debouncing]

**Learning:** Replaced ad-hoc timers and inline debouncing loops with a centralized `debounce` utility in `js/utils/debounce.js` to enhance performance during high-frequency events like window resize and scroll.
**Action:** Always utilize the central debounce utility to prevent redundant layouts and style recalculations that block the main thread.

## 2025-03-12 - [Continuous Event Optimizations]

**Learning:** Using `debounce` on continuous high-frequency layout events like `scroll` causes UI jank and unresponsive continuous scrolling. Instead, `requestAnimationFrame` paired with a boolean `ticking` lock limits execution perfectly to the screen refresh rate, preserving responsiveness. `debounce` is better suited for less continuous events like `resize`.
**Action:** Use `requestAnimationFrame` + `ticking` lock for `scroll` and `mousemove` layout handlers, but stick to `debounce` for `resize` or user input delays.

## 2025-03-14 - [Avoiding Redundant Object Instantiation in Hot Render Loops]

**Learning:** When drawing charts or animations that loop over large datasets on every frame, re-instantiating objects like `new Date(...)` or calling parsing methods like `.getTime()` inside the loop for every data point creates massive garbage collection pressure and main thread overhead.
**Action:** Always verify if parsed/formatted data structures (like pre-computed timestamp arrays) already exist outside the hot loop and reuse them via direct index lookups instead of duplicating parsing work.

## 2025-03-15 - O(1) Table Row Hover Lookup

**Learning:** In applications where table rows have hover effects driven by mouse tracking, continuously resolving hovered rows via `document.elementFromPoint(e.clientX, e.clientY)` followed by an O(N) `findIndex` lookup over row collections causes severe layout thrashing and main-thread blocking, particularly with large datasets.
**Action:** Always prefer retrieving the interacted element via `e.target` directly in mouse events. Pair this with a `WeakMap` during initialization to associate DOM nodes to their corresponding index or metadata for O(1) constant-time lookup instead of iterating through arrays.
