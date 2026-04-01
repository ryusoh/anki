Plan:

1. Module A: Structural Health.
   - Refactor `enhance_main_window/tree.py` to consolidate multiple sequential `SELECT` statements into a single query per target table using conditional aggregation (`SUM(CASE WHEN condition THEN expression ELSE NULL END)`).
   - Wait! For counts, if `addend` is empty, the expression is `1`, so `SUM(CASE WHEN condition THEN 1 ELSE NULL END)`. Or `COUNT(CASE WHEN condition THEN 1 ELSE NULL END)`.
   - Update the dictionary conditionally to preserve sparse keys (only populating result keys if count > 0 or sum is not None).

2. Module B: Resilience & Error Handling.
   - Refactor `review_heatmap/libaddon/packaging.py` empty `pass` in `except ImportError` blocks. Replace with `logger.debug("ImportError message")` to make silent failures visible without changing control flow. Add `from .debug import logger` to the file.

3. Module C: Code Hygiene.
   - Address "market calendar logic or holiday adjustments":
     - Implement Good Friday calculation (via Easter Computus logic) in `js/utils/date.js` `isTradingDay` to correctly handle this missing US market holiday.
   - Wait, `js/utils/smoothing.js` has `TODO`? The memory says: "avoid chaining array methods... Use a single `for` loop". BUT `js/utils/smoothing.js` was already refactored by Bolt to use a single `for` loop! (Wait, let me double check my output: `// Bolt: Pre-calculate maxDistance outside the loop`). It already is done. So what's left for Code Hygiene? "Implement pending TODO items that relate to core system accuracy (e.g., market calendar logic or holiday adjustments)." I'll add Good Friday computation.

4. Run Linters and Tests.
   - Run `make check`, `make lint` before and after changes.

5. Pre-commit
   - Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done.

6. Submit PR without user interaction.
