# Accessibility Learnings

## 2024-03-01 - Terminal Input Accessibility

**Learning:** Terminal emulator inputs often lack proper `<label>` associations because the visual prompt (like `user@host:~$`) isn't conventionally treated as a label in HTML. This makes it difficult for screen reader users to understand the input's context.
**Action:** When building terminal-like UI or command line inputs, always convert the visual prompt span into a `<label for="...">` and add a clear `aria-label` to the input field itself describing its specific purpose (e.g., "Terminal command input").

## 2024-05-15 - Missing ARIA References in Static HTML

**Learning:** It is common for elements to use `aria-labelledby` or `aria-describedby` referencing an ID that was forgotten or removed during refactoring, resulting in a broken accessibility experience where screen readers announce nothing.
**Action:** Always verify that the ID referenced by `aria-labelledby` or `aria-describedby` actually exists in the DOM. If the visual design doesn't call for a visible title, inject a screen-reader-only (`sr-only`) element with that ID to satisfy the accessibility requirement without altering the visual layout.

## 2024-03-15 - Focus-Visible for Screen Reader Only Elements

**Learning:** Using standard `:focus` on `.sr-only` elements like "skip-to-content" links can inadvertently trigger visual focus outlines when users click the element or its vicinity with a mouse, leading to a confusing mouse navigation experience.
**Action:** Standardize on the `:focus-visible` pseudo-class for keyboard-specific accessibility elements to ensure focus styles are strictly applied during keyboard navigation, maintaining a clean UI for mouse users while preserving accessibility.
\n## 2024-05-24 - Interactive Table Headers Keyboard Accessibility\n\n**Learning:** Table headers (`th` elements) that act as buttons for sorting or filtering (e.g., using `.sortable` or `.filterable` classes) are not inherently keyboard accessible. Screen reader and keyboard-only users cannot interact with them using Tab, Enter, or Space.\n**Action:** When making table headers interactive, ensure they are focusable by adding `tabindex="0"` and `role="button"`. Furthermore, always provide equivalent keyboard event listeners (like `keydown` for Enter and Space) alongside the mouse `click` listeners.

## 2025-03-01 - Keyboard Accessibility for Dynamically Created Elements

**Learning:** When dynamically generating interactive elements like dropdown menus via JavaScript (e.g., `document.createElement('div')`), these elements inherently lack the accessibility features of native interactive elements like `<button>`. They cannot receive keyboard focus or be activated by keyboard inputs.
**Action:** Always manually apply interactive attributes (`role="button"`, `tabindex="0"`) to dynamically created clickable non-semantic elements. Additionally, attach explicit `keydown` listeners specifically for `Enter` and `Space` keys to duplicate the activation logic normally handled by `click` events.

## 2024-03-18 - Keyboard Accessibility for Chart Legends

**Learning:** The interactive chart legends (e.g., toggling benchmarks in the performance chart) were built using generic `div` elements with only mouse `click` listeners. They lacked keyboard navigation and screen reader state tracking, meaning keyboard users could not filter or toggle chart data sets.
**Action:** When creating custom interactive toggles with `div` or `span` elements, always add `role="button"`, `tabIndex=0`, appropriate `aria-pressed` states, and a combined `keydown` handler for the 'Enter' and 'Space' keys.

## 2024-05-30 - Terminal Live Output Screen Reader Accessibility

**Learning:** Emulated terminal outputs that continuously append new text lines dynamically (e.g., via `appendChild`) are completely silent to screen readers unless explicitly marked as a live region. This creates a severe accessibility barrier where visually impaired users cannot perceive command responses or real-time logs.
**Action:** When building custom terminal or log viewer UIs, always add `role="log"`, `aria-live="polite"`, and `aria-atomic="false"` to the scrolling container element (`div.terminal-output`). This ensures screen readers correctly queue and announce new lines of text as they appear without interrupting the user.

## 2025-03-20 - Terminal Emulator Output Accessibility

**Learning:** Terminal emulators or command-line interfaces built with web technologies that dynamically append command output and results using JavaScript are entirely invisible to assistive technologies like screen readers if no ARIA live regions are used. Without explicit indication, screen reader users input a command, hit enter, and receive absolutely no feedback.
**Action:** When building custom web-based terminal interfaces or logs, always ensure the container holding the output stream uses `role="log"` and `aria-live="polite"` so new lines are announced without interrupting the user. Additionally, route dedicated command error messages to a container with `aria-live="assertive" role="alert"` to immediately interrupt and alert the user of failure.

## 2023-10-24 - Dynamic ARIA Live Regions vs Global Elements

**Learning:** Reusing a single global static HTML element (like `<div id="error">`) for ARIA live region announcements (e.g., `role="alert" aria-live="assertive"`) can be risky. Changing its visual display properties or DOM position to handle dynamic errors (like terminal outputs) can break the visual experience for sighted users or conflict with existing error-handling logic.
**Action:** When dynamically appending text that needs immediate screen reader announcement (like terminal error lines), it is safer and more robust to inject the `role="alert"` and `aria-live="assertive"` attributes directly onto the newly created specific DOM elements (e.g., the `div.line` representing the error) rather than modifying global error containers.

## 2024-05-31 - Keyboard Accessibility for Navigation Links

**Learning:** When custom styling navigation links or buttons requires removing default browser outlines (`outline: none`), it breaks keyboard navigation accessibility because users can no longer perceive which element has focus.
**Action:** Always restore keyboard accessibility by adding a `:focus-visible` pseudo-class with a distinct outline (e.g., `outline: 2px solid rgba(255, 255, 255, 0.5)`) so keyboard users can perceive focus without affecting mouse users.

## 2024-05-31 - Range Input Slider Accessibility

**Learning:** When building custom interactive components like timelines with `<input type="range">`, the native input often lacks context for screen reader users because its surrounding visual context (like floating date tooltips or min/max bounds) isn't semantically linked.
**Action:** Always provide an explicit `aria-label` (e.g., "Timeline progress slider") or use `aria-labelledby` for range inputs to ensure screen reader users understand the specific purpose of the control.

## 2024-06-05 - ARIA Sort States on Table Headers

**Learning:** When making table headers (`th` elements) sortable, overriding their inherent `columnheader` role by adding `role="button"` breaks their ability to convey sorting state to screen readers. `aria-sort` is only a valid attribute on elements with `columnheader` or `rowheader` roles.
**Action:** Do not use `role="button"` on interactive `th` elements. Instead, apply `tabindex="0"` for keyboard accessibility and initialize them with `aria-sort="none"` (or `ascending`/`descending` as appropriate) to correctly expose the sortable semantics and state.

## 2026-05-16 - ARIA Sort States on Table Headers Fix

**Learning:** When making table headers (`th` elements) sortable, overriding their inherent `columnheader` role by adding `role="button"` breaks their ability to convey sorting state to screen readers. `aria-sort` is only a valid attribute on elements with `columnheader` or `rowheader` roles.
**Action:** Do not use `role="button"` on interactive `th` elements. Instead, apply `tabindex="0"` for keyboard accessibility and initialize them with `aria-sort="none"` (or `ascending`/`descending` as appropriate) to correctly expose the sortable semantics and state.

## 2024-06-08 - Screen Reader Redundancy with Icon Links

**Learning:** FontAwesome icons (`<i class="fa ...">`) placed inside semantic interactive elements like `<a aria-label="...">` are often read out loud by screen readers as arbitrary Unicode characters or irrelevant text, which adds confusing noise and redundancy when an `aria-label` already perfectly describes the element's purpose.
**Action:** Always explicitly hide decorative or redundant icon elements from screen readers by adding `aria-hidden="true"` to the `<i>` or `<svg>` tag when the parent interactive element already provides an adequate accessible name via `aria-label` or text content.

## 2024-06-09 - Range Input Focus Visibility

**Learning:** Native `<input type="range">`, especially when styled with `outline: none`, becomes invisible to keyboard users as they navigate through the UI, breaking accessibility.
**Action:** Always ensure that range inputs have an explicit `:focus-visible` style defined (e.g., `outline: 2px solid rgba(255, 255, 255, 0.8)`) so keyboard focus remains perceptible to the user.
