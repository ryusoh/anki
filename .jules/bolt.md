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

## 2025-03-22 - [Optimizing Hot Path Array Copying]

**Learning:** Deeply cloning arrays of objects (`lots.map((l) => ({ ...l }))`) inside hot inner loops like transaction FIFO calculations creates massive intermediate object allocations and Garbage Collection pressure, scaling poorly (O(n) memory allocation inside O(n) loops).
**Action:** When calculating cumulative or sequential state across thousands of records, modify the accumulator state arrays in-place when safely scoped to a single computational pass, instead of recreating them on every iteration.

## 2025-03-27 - [Optimize Polynomial Fitting in Smoothing Utility]

**Learning:** When performing mathematical operations over arrays (like polynomial fitting), using multiple chained `Array.prototype.reduce()` calls to compute sums (e.g., sumX, sumY, sumXY) introduces significant overhead. Each `.reduce()` call requires a new function allocation and iterates over the array independently, leading to O(k\*N) time complexity and unnecessary GC pressure.
**Action:** Replace multiple chained `.reduce()` passes with a single O(N) `for` loop to compute multiple aggregates simultaneously, particularly in performance-critical or high-frequency calculation paths.

## 2025-03-29 - [Optimizing Object Allocation in Map/Filter Chains]

**Learning:** Chaining array methods like `.map().filter()` inside rendering or calculation loops creates excessive intermediate array allocations. When combined with object creation inside the `.map()` (such as `{ index, date: new Date(...) }` or `{ ...d, date: new Date(...) }`), these discarded intermediate objects cause severe Garbage Collection pressure and block the main thread.
**Action:** Replace `O(N)` map+filter chains with a single `for` loop. Compute required values (like timestamps) directly inside the loop and only push to the result array if the condition passes, avoiding intermediate objects and minimizing Date instantiations.
