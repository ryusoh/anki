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

## 2025-03-16 - [Synchronous preventDefault in Throttled Events]

**Learning:** When using `requestAnimationFrame` + `ticking` lock to throttle high-frequency events like `pointermove` or `touchmove`, calling `event.preventDefault()` inside the deferred animation frame callback can fail or cause passive event listener warnings in browsers, as it's no longer synchronous with the event dispatch. This leads to unwanted default behaviors (like scrolling) triggering intermittently on touch devices.
**Action:** Always extract and execute `event.preventDefault()` synchronously _before_ the `requestAnimationFrame` deferral when throttling user input events.

## 2024-05-19 - Caching DOM queries in scroll handlers

**Learning:** High-frequency event handlers like `scroll` and `resize` (even when debounced or throttled with `requestAnimationFrame`) can cause performance issues if they repeatedly query the DOM using `document.querySelector` or `getElementById`.
**Action:** Cache DOM element references outside the event handler scope or lazily initialize them once to avoid repeated main-thread blocking DOM lookups during layout calculations.

## 2025-03-19 - [Optimize Monte Carlo Metric Computation]

**Learning:** In Web Workers dealing with thousands of simulation paths (like Monte Carlo simulations), using array methods that create intermediate allocations (e.g., `.slice()`) chained with multiple passes (e.g., repeated `.reduce()`) adds significant memory and Garbage Collection overhead.
**Action:** Replace chained, multi-pass array methods with a single O(N) `for` loop to compute multiple aggregate metrics simultaneously, saving memory and processing time without sacrificing correctness.

## 2025-03-22 - [Optimizing Hot Path Loops]

**Learning:** When performing chained array manipulations (like `.filter().reduce()`) on an array nested inside another high-frequency loop (e.g., parsing transactions), recreating invariant objects like `new Date(transactionDate)` inside the inner `.filter()` closure is extremely expensive. It results in millions of redundant Date object instantiations and heavy GC pressure.
**Action:** Always pre-calculate invariant values (like timestamps from strings) outside the hot inner loop, and prefer a single O(N) `for` loop over chained array methods to avoid intermediate array allocations and closure overhead on performance-critical paths.
