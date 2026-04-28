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

## 2025-04-01 - [Schwartzian Transform for Expensive Sorting]

**Learning:** When sorting large arrays using custom comparator functions that perform expensive calculations (like parsing dates with `new Date(...)`), doing these calculations directly inside the `.sort((a, b) => ...)` comparator creates a massive performance bottleneck. Because `sort` can compare each element multiple times (O(N log N)), these expensive operations are executed repeatedly, causing heavy Garbage Collection pressure and blocking the main thread.
**Action:** Always use the Schwartzian transform (decorate-sort-undecorate pattern) when sorting by expensive computed values. Pre-calculate the values once per item in a single O(N) pass, sort the decorated array, and then extract the original items.

## 2024-05-24 - [Pre-processing arrays for O(1) lookups in loops]

**Learning:** In `js/transactions/calculations.js`, the `computeRunningTotals` function was scanning the `splitHistory` array iteratively for each transaction processed (via `applyTransactionFIFO` -> `getSplitAdjustment`), which degrades to O(N \* M) performance where N is transactions and M is split entries. For large datasets this caused substantial slowdowns and GC pressure.
**Action:** When a function requires repeatedly checking an auxiliary array inside a hot loop, create a pre-processed `Map` grouping items by their key symbol outside the loop, reducing inner lookups from O(M) to O(K) where K is the number of splits for a single symbol (effectively O(1)).

## 2024-05-30 - [Optimize loop array copying to prevent regressions]

**Learning:** Reverting to generic functionally chained arrays without object construction is not measurable performance, but correctly tracking the memory space via object instantiations inside loops with high frequencies (like charts arrays) does affect Main Thread performance.
**Action:** When manually fusing `.map().filter()` into `for` loops, correctly memoize and limit object instantiation (like `{ ...item }`) exclusively to elements that pass the filter conditional logic, preserving both rendering performance and original side effects.

## 2025-04-09 - [Optimizing Dynamic Array allocations and Iterations]

**Learning:** Allocating array iteratively and mapping it sequentially, when working with Object.entries inside loops, can easily lead to memory bloat by redundantly allocating empty arrays or mapping over the entire dimension length. Avoiding conditional Array constructions when `valueMode !== "absolute"` eliminates the allocation inside the loop entirely when disabled.
**Action:** Always conditionally allocate arrays specifically inside iterations only if the values they capture are required. Avoid unconditional new Array(N) pre-allocations if their values can be derived lazily or discarded.

## 2025-05-18 - [Optimizing Hot Path Array Copying inside Canvas Rendering Loop]

**Learning:** Re-instantiating `cumulativeValues` using `.map()` on every single ticker iteration during the `renderCompositionChartWithMode` Canvas render frame creates tremendous Garbage Collection pressure. For a chart with 100 tickers and 500 dates, `cumulativeValues = cumulativeValues.map(...)` instantiates 100 arrays of 500 items on _every single frame_ the chart renders, leading to heavy GC stalls.
**Action:** When calculating running totals inside rendering loops or hot paths, mutate the accumulator arrays in-place using a single O(N) `for` loop instead of creating entirely new array references.

## 2025-05-18 - [Optimizing Hot Path Filters in Table Render Loops]

**Learning:** Chaining `.filter()` array methods to process search and command-palette tokens in a table render loop (`filterAndSort` in `js/transactions/table.js`) creates significant Garbage Collection pressure and slows down layout calculations due to intermediate array allocations on every pass. For large datasets with frequent user input, this causes main-thread blocking and UI jank.
**Action:** Replace `O(N)` chained filter array passes with a single `for` loop. Apply the filter conditionals with early `continue` statements to bypass items, only pushing to the final result array once, which prevents intermediate array instantiations and minimizes overhead.

## 2025-05-18 - [Optimizing Hot Path Array Copying inside Loop]

**Learning:** Re-instantiating `chronologicalTransactions` using `.map().sort().map()` chaining creates significant Garbage Collection pressure and slows down layout calculations due to intermediate array allocations on every pass. For large datasets with frequent user input, this causes main-thread blocking and UI jank.
**Action:** Replace `O(N)` chained array passes with a single `for` loop. Pre-allocate the array and use in-place `.sort()` to bypass intermediate array instantiations and minimize overhead.

## 2025-05-18 - [Optimizing chained .reduce() in array loops]

**Learning:** When calculating two or more aggregated values (like total quantity and weighted sum) over the same array using separate chained `.reduce()` passes, it forces the runtime to iterate the array multiple times and allocate callbacks for each item. This increases CPU cycles and creates unnecessary garbage collection pressure on frequently computed stats.
**Action:** Replace multiple chained `.reduce()` passes over the same array with a single standard `for` loop to compute all needed aggregates simultaneously, optimizing O(2N) down to O(N) and eliminating closure allocation overhead.

## 2024-03-24 - Optimize chained array map allocations in reviews.js

**Learning:** Found multiple instances where arrays were being transformed multiple times with chained `.map()` calls, generating unnecessary intermediate arrays and putting pressure on garbage collection. This is a common performance anti-pattern.
**Action:** Replaced chained `.map()` operations with a single `for` loop that iterates over the source array once and populates a pre-allocated array (`new Array(length)`), executing all formatting and accumulation logic concurrently. Apply this pre-allocation + single loop pattern for hot path array derivations across the app.

## 2025-05-18 - [Optimize Tooltip Iterations in Chart Render callbacks]

**Learning:** When defining `callbacks: { title: (items) => items.map(item => item.label).join('\n') }` within interactive libraries like Chart.js tooltips, chained array mapping and joining during high-frequency mouse hover operations cause numerous intermediate Array allocations and heavy Garbage Collection spikes in hot paths.
**Action:** Replace `.map().join()` with standard `.length` iteration inside interactive callback functions. Iteratively construct primitive strings with standard string concatenation and a single native `for` loop to eliminate intermittent Array heap allocations completely.

## 2025-05-19 - [Optimize flatMap Array loops]

**Learning:** When calculating max values using `Object.values(data).flatMap(entries => entries.map(e => e.day))`, multiple chained iterations create extensive array instantiation allocations on the heap, and put heavy load on GC due to discarding intermediate array states during layout rendering.
**Action:** Use native primitive standard iteration to bypass `.flatMap()` entirely, creating 0 new intermediate array allocations.

## 2026-04-28 - [Optimizing Hot Path Maps in Set Initializations]

**Learning:** When generating a Set of unique properties from an array (like unique decks), doing `[...new Set(data.nodes.map(n => n.deck))]` maps an entirely new temporary array in memory purely to feed the Set constructor, creating severe and unnecessary Garbage Collection overhead when parsing large datasets.
**Action:** Use a fast native `for` loop to iteratively `add()` values into a `new Set()` directly, entirely bypassing the intermediate array `.map()` allocation step when extracting unique properties.
