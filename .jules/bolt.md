## 2025-05-18 - [Avoiding Chained Array Methods in Hot Paths]

**Learning:** When sorting and iterating over large data collections in hot paths (like `computeRunningTotals`), chaining array methods like `.map().sort().map()` or using `Array.from().reduce()` creates intermediate array allocations that add substantial memory overhead and trigger expensive Garbage Collection (GC) cycles, degrading overall performance.
**Action:** Replace functional array method chains with explicit, pre-allocated array loops (e.g., the Schwartzian transform for sorting) and `for...of` loops for reduction. This pattern minimizes intermediate allocations and GC pressure while ensuring O(N) linear time processing in performance-critical code.

## 2024-04-14 - [Avoiding Chained Array Methods in Hot Paths]

**Learning:** When sorting and iterating over large data collections in hot paths (like `computeRunningTotals`), chaining array methods like `.map().sort().map()` or using `Array.from().reduce()` creates intermediate array allocations that add substantial memory overhead and trigger expensive Garbage Collection (GC) cycles, degrading overall performance.
**Action:** Replace functional array method chains with explicit, pre-allocated array loops (e.g., the Schwartzian transform for sorting) and `for...of` loops for reduction. This pattern minimizes intermediate allocations and GC pressure while ensuring O(N) linear time processing in performance-critical code.
