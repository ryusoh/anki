## 2024-05-19 - Cache window.getComputedStyle inside TableGlassEffect resize handling

**Learning:** Calling `window.getComputedStyle(this.container)` multiple times sequentially (or separated by brief DOM lookups) forces redundant synchronous style recalculations on the main thread, especially inside initialization or resize hooks where layout is already invalidated.
**Action:** Always call `window.getComputedStyle()` once, cache the result to a local variable, and read multiple properties from that cached object to prevent main thread blocking and layout thrashing.
