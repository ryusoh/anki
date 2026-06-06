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

## 2024-06-15 - Cyclomatic Complexity and Error Resilience Audit

**Learnings:**

- **Structural Health:** Refactored complex search logic functions in `prioritize_front_field_search/search.py` (`extract_terms` and `build_tier1_query`) by extracting repetitive conditionals into internal helpers (`_extract_term_from_field`, `_process_query_part`, `_transform_tier1_part`). This significantly lowered their cyclomatic complexity (from C down to B and A grades in radon) and improved their readability without altering test behavior.
- **Structural Health:** Streamlined `_gather_future_due` in `stats_page_customizer/__init__.py` by breaking out the database fetching and payload mapping logic into helper functions.
- **Silent Failures:** Replaced remaining bare `except:` blocks in `data/anki/upload-to-r2` and `review_heatmap/libaddon/_vendor/logging/__init__.py` with specific `except Exception` blocks and context-aware error prints to ensure tracebacks are caught securely but not suppressed blindly.

**Action:** Consistently break down query generation loops into discrete sub-functions for filtering logic, and always attach exceptions to logged warnings when patching legacy `except:` clauses.

- **Structural Health:** Refactored `enhance_main_window/node.py` methods `renderDeckTree`, `_columnDisplayData`, and `setEmpty` by extracting header rendering, data resolution, and child state checking logic. These functions were extremely long and nested but are now broken down into simple, composable helper methods that achieve radon B and A grades.
- **Silent Failures:** Fixed remaining bare `except Exception:` blocks in `tools/security_audit.py` (JSON/file reading), `awesome_tts/awesometts/service/ispeech.py` (error parsing), `awesome_tts/awesometts/service/base.py` (response payload setup), and `awesome_tts/awesometts/gui/listviews.py` (rule regex compilation). By passing these exceptions to our standard loggers (`print/logging.getLogger`), we ensure debugging context is retained while maintaining necessary fallback behaviors.

- **Silent Failure Audit:** To improve resilience, located and fixed empty catch blocks and generic error suppressions (`except Exception:`) across Python and JavaScript files (`data/anki/security_check.py`, `data/anki/upload-to-r2`, `data/anki/fetch`, `js/mobile_ambient_bootstrap.js`, `js/ui/videoFallback.js`). These were updated to explicitly capture the error object and log it with context using `print` or `console.warn` (respecting linter rules with `eslint-disable-next-line`), ensuring silent failures are now visible.

## 2024-05-14 - Structural Health & Code Hygiene

**Learning:** When executing Code Health & Cleanup tasks ('Architect' / 'Janitor' roles), focus on reducing cyclomatic complexity (e.g., verified via `radon`), replacing empty `catch`/`except` blocks with context-aware logging, and pruning dead code/TODOs.
**Action:** Consistently replace bare `except:` with `except Exception as e: logging.getLogger(__name__).debug(e)` and ensure long multple condition methods are extracted to helper functions.

## 2024-05-18 - Scheduled Task: Code Health & Cleanup

**Learnings:**

- **Structural Health:** Refactored `on_browser_did_search` in `prioritize_front_field_search/__init__.py`. Extracted the complex SQL query execution and field parsing logic into a helper function `_fetch_front_fields(col, all_sorted_ids, is_notes_mode)`. This reduced cyclomatic complexity significantly and improved maintainability.
- **Silent Failures:** Audited codebase for empty `except:` blocks and `except Exception:` blocks where errors were suppressed. Added logging to `rewrite_text_of_study_cards/shige_config/shige_addons.py`, `enhance_main_window/node.py` and `js/graph/graph.js` to ensure tracebacks are caught securely but not suppressed blindly.
- **Cleanup Logic:** Cleaned up pending `TODO: NewDeckStats` entries in `review_heatmap/views.py` and `review_heatmap/web_bridge.py` by introducing conditional support for `aqt.stats.NewDeckStats` if the attribute exists on `aqt.stats` in the user's specific Anki version.

**Action:** Continually audit cyclomatic complexity using `radon` when touching large legacy Python functions, and always attach exceptions to logged warnings when patching legacy `catch` or `except:` clauses.

## 2024-05-19 - Code Health & Cleanup

**Learnings:**

- **Structural Health:** Refactored complex multi-conditional functions to dramatically reduce cyclomatic complexity using `radon`. In `auto_wiktionary/utils.py`, `parse_wiktionary_html` (F grade, 56 complexity) was broken down into manageable helpers (B grade). In `data/anki/generate_review_stats.py`, `aggregate_reviews` (D grade, 25 complexity) had logic extracted for stat accumulation. In `strip_html_tags/__init__.py`, `_strip_selection` (F grade, 46 complexity) was simplified into six helper functions (C grade).
- **Silent Failures:** Identified and fixed empty `except Exception:` blocks in `auto_image/utils.py` that were suppressing API and network errors during DuckDuckGo image searches and downloads. Properly bound `except Exception as e:` and logged using `logging.getLogger(__name__)` to retain debugging context while maintaining control flow.

**Action:** Continually execute `radon cc -s` audits to ensure functions maintain C grade or better. Always instantiate a module logger and log tracebacks when implementing fallback logic inside generic exception handlers.

- **Silent Failures:** Replaced bare `except:` blocks in `highlight_search_matches/__init__.py` with `except Exception as e:` and logged the exception context via `logging.getLogger(__name__).debug` to maintain visibility into configuration fetch errors or debug log write errors.
- **Structural Health:** Refactored `_accept_process` in `awesome_tts/awesometts/gui/stripper.py` to extract note processing logic into `_process_notes` and summary generation into `_build_messages`, dropping main method cyclomatic complexity from 19 to 3 and enhancing modularity.
  **Learning:** Cyclomatic complexity can quickly accumulate in UI callback functions that handle both business logic and alert rendering. Extracting formatting tasks simplifies testing and debugging.
  **Action:** When auditing `accept` or process callbacks in PyQt dialogs, eagerly separate data mutation logic from presentation text formatting.

- **Resilience & Error Handling:** Fixed empty `except` blocks (`pass`) in multiple modules (`graph/export_data.py`, `data/anki/security_check.py`, `prioritize_front_field_search/__init__.py`, `awesome_tts/awesometts/gui/base.py`, `awesome_tts/awesometts/machineid.py`, `review_heatmap/web_bridge.py`) by replacing them with context-aware logging or warnings.
- **Structural Health:** Reduced cyclomatic complexity of `Service.net_stream` in `awesome_tts/awesometts/service/base.py` and `ServiceDialog._on_service_activated` in `awesome_tts/awesometts/gui/base.py` by extracting target parsing, response validation, group activation, and panel setup logic into smaller sub-methods.

## 2026-06-06 - Structual Health Refactor using AST and safer abstractions

**Learnings:**

- **Refactoring Strategy:** Refactoring complex scripts containing large multi-line strings (`data/anki/upload-to-r2`) using regex (`re.sub`) or string matching is highly brittle and often leads to syntax errors (unterminated string literals, f-string bugs).
- **Structural Health:** Attempted to reduce cyclomatic complexity in `data/anki/upload-to-r2` (`main` graded F) but regex-based extraction corrupted the file. Restored the file to its original state to maintain 100% test passing rate (`make check-py`).

**Action:** When extracting functions from complex legacy scripts that have large literal blocks, avoid automated regex replacements. Either use AST-based refactoring tools, or manually rewrite the target function using Python block parsing. Always ensure 100% test passing before committing any code changes.
