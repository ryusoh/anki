## 2024-03-27 - Technical Debt & Code Hygiene Sweep

**Learnings:**

- **Silent Failures:** Identified and fixed several empty `except:` blocks across `tools/security_audit.py`, `review_heatmap/activity.py`, and `review_heatmap/libaddon/config/manager_old.py`. It is critical to log context (e.g. `print(f"Failed to load local config: {e}")`) or add explicit comments (`pass # Fallback to 2.1 sched_ver()`) to maintain error resilience and debugging capabilities without altering control flow. Catching raw `Exception` instead of bare `except:` prevents suppressing system-exiting signals like `KeyboardInterrupt`.
- **Cleanup Logic:** Implemented missing market calendar and holiday adjustments for US markets in `js/utils/date.js` (e.g., Juneteenth, MLK Jr. Day, Memorial Day) to ensure accurate trading day calculations. Adding these boundary edge-cases drastically improves the accuracy of downstream financial metrics and analysis, and required careful integration into `tests/date.test.js`.
  **Action:** Always provide explicit reasoning for suppressed errors, avoid bare `except:` clauses, and ensure date math explicitly handles fixed and floating schedule holidays.
