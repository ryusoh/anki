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
