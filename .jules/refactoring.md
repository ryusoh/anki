## 2024-03-27 - Technical Debt & Code Hygiene Sweep

**Learnings:**

- **Silent Failures:** Identified and fixed several empty `except:` blocks across `tools/security_audit.py`, `review_heatmap/activity.py`, and `review_heatmap/libaddon/config/manager_old.py`. It is critical to log context (e.g. `print(f"Failed to load local config: {e}")`) or add explicit comments (`pass # Fallback to 2.1 sched_ver()`) to maintain error resilience and debugging capabilities without altering control flow. Catching raw `Exception` instead of bare `except:` prevents suppressing system-exiting signals like `KeyboardInterrupt`.
- **Cleanup Logic:** Implemented missing market calendar and holiday adjustments for US markets in `js/utils/date.js` (e.g., Juneteenth, MLK Jr. Day, Memorial Day) to ensure accurate trading day calculations. Adding these boundary edge-cases drastically improves the accuracy of downstream financial metrics and analysis, and required careful integration into `tests/date.test.js`.
  **Action:** Always provide explicit reasoning for suppressed errors, avoid bare `except:` clauses, and ensure date math explicitly handles fixed and floating schedule holidays.

## 2026-03-30 - Cyclomatic Complexity & Error Handling Sweep

**Learnings:**

- **Silent Failures:** Fixed remaining bare `except:` and generic `except Exception:` blocks in `awesome_tts` and `tabbed_stats` plugins that were swallowing errors without logging. Logging the exception allows easier debugging while still ignoring the error for control flow.
- **Structural Health:** Refactored `tools/security_audit.py` to extract large `check_for_private_data` and `main` functions into smaller, more testable components, significantly reducing cyclomatic complexity while maintaining existing behavior.
- **Cleanup Logic:** Added the Easter Computus logic to accurately identify "Good Friday" as a major fixed US market holiday in `js/utils/date.js` based on pending TODOs related to market calendar logic.

**Action:** Continue to extract complex multi-conditional statements into smaller functions with descriptive names, and always log errors in broad `except` blocks.

## 2024-05-15 - Error Handling & Cyclomatic Complexity Health Sweep

**Learnings:**

- **Silent Failures:** Replaced remaining bare `except:` blocks with `except Exception:` (or `except ImportError:`) across `awesome_tts`, `custom_background`, `enhance_main_window`, and `rewrite_text_of_study_cards`. This prevents accidental suppression of system-exiting signals (`KeyboardInterrupt`, `SystemExit`) while keeping intended error fallback paths intact.
- **Structural Health:** Refactored `data/anki/security_check.py` to extract complex multi-conditional scanning logic (`_scan_tracked_file` and `_check_json_data`). This significantly reduced cyclomatic complexity within the `main` loop and fixed a latent bug where the script attempted to load `.json.gz` files via an un-resolved relative path instead of `full_path`.
- **Code Hygiene:** Refactored `xxx_todo_changeme` variables in `awesome_tts/awesometts/__init__.py` to use descriptive names (`preset_item`, `group_item`), removing residual technical debt from automated `2to3` migrations.

**Action:** Continue replacing generic `except:` statements across the codebase, always use contextually-aware exceptions like `ImportError` where applicable, and maintain smaller cyclomatic footprints in critical path functions.

## 2026-04-04 - Code Health & Error Handling

**Learning:** Avoid bare `except:` blocks as they catch system exceptions like `KeyboardInterrupt`. Use `except Exception:` to restrict error catching to application errors while maintaining the required fallback control flow.
**Action:** Consistently replace bare `except:` with `except Exception:` and ensure comments or logging exist for fallback logic.
