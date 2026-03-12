## 2024-03-01 - Terminal Input Accessibility

**Learning:** Terminal emulator inputs often lack proper `<label>` associations because the visual prompt (like `user@host:~$`) isn't conventionally treated as a label in HTML. This makes it difficult for screen reader users to understand the input's context.
**Action:** When building terminal-like UI or command line inputs, always convert the visual prompt span into a `<label for="...">` and add a clear `aria-label` to the input field itself describing its specific purpose (e.g., "Terminal command input").
