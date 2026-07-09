import test, { describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import { JSDOM } from "jsdom";

describe("icon_font_ready", () => {
  let dom;
  let originalFonts;
  let originalConsoleWarn;
  let activeTimers = [];

  beforeEach(() => {
    dom = new JSDOM("<!DOCTYPE html><html><body></body></html>", { url: "http://localhost" });
    globalThis.window = dom.window;
    globalThis.document = dom.window.document;
    originalFonts = dom.window.document.fonts;
    originalConsoleWarn = globalThis.console.warn;
    globalThis.console.warn = () => {};

    activeTimers = [];
    dom.window.setTimeout = (cb, delay) => {
      activeTimers.push({ cb, delay });
      return activeTimers.length;
    };
    dom.window.clearTimeout = (id) => {
      // no-op
    };
  });

  afterEach(() => {
    globalThis.console.warn = originalConsoleWarn;
    if (dom && dom.window) {
      Object.defineProperty(dom.window.document, "fonts", {
        value: originalFonts,
        writable: true,
        configurable: true,
      });
    }
    delete globalThis.window;
    delete globalThis.document;
  });

  async function loadIconFontReady() {
    await import(`../js/ui/icon_font_ready.js?t=${Date.now()}`);
  }

  function mockDocumentFonts(mockValue) {
    Object.defineProperty(dom.window.document, "fonts", {
      value: mockValue,
      writable: true,
      configurable: true,
    });
  }

  test("adds ready class immediately if font is already checked and loaded", async () => {
    mockDocumentFonts({
      check: () => true,
      load: () => {},
      ready: Promise.resolve(),
    });

    await loadIconFontReady();

    assert.strictEqual(document.body.classList.contains("icon-font-ready"), true);
  });

  test("adds ready class if ready promise rejects", async () => {
    let resolveLoad;
    const loadPromise = new Promise((r) => { resolveLoad = r; });
    let rejectReady;
    const readyPromise = new Promise((_, r) => { rejectReady = r; });
    readyPromise.catch(() => {});

    mockDocumentFonts({
      check: () => false,
      load: () => loadPromise,
      ready: readyPromise,
    });

    await loadIconFontReady();

    assert.strictEqual(document.body.classList.contains("icon-font-ready"), false);

    resolveLoad([]);
    rejectReady(new Error("Ready failed"));

    await new Promise((r) => setTimeout(r, 0));

    assert.strictEqual(document.body.classList.contains("icon-font-ready"), true);
  });

  test("waits for font load and adds ready class", async () => {
    let resolveLoad;
    const loadPromise = new Promise((r) => { resolveLoad = r; });
    let resolveReady;
    const readyPromise = new Promise((r) => { resolveReady = r; });
    mockDocumentFonts({
      check: () => false,
      load: () => loadPromise,
      ready: readyPromise,
    });

    await loadIconFontReady();

    assert.strictEqual(document.body.classList.contains("icon-font-ready"), false);

    resolveLoad([]);
    resolveReady();

    await new Promise((r) => setTimeout(r, 0));

    assert.strictEqual(document.body.classList.contains("icon-font-ready"), true);
  });

  test("adds ready class if font load fails", async () => {
    let rejectLoad;
    const loadPromise = new Promise((_, r) => { rejectLoad = r; });
    loadPromise.catch(() => {});
    let resolveReady;
    const readyPromise = new Promise((r) => { resolveReady = r; });
    mockDocumentFonts({
      check: () => false,
      load: () => loadPromise,
      ready: readyPromise,
    });

    await loadIconFontReady();

    assert.strictEqual(document.body.classList.contains("icon-font-ready"), false);

    rejectLoad(new Error("Font load failed"));
    resolveReady();

    await new Promise((r) => setTimeout(r, 0));

    assert.strictEqual(document.body.classList.contains("icon-font-ready"), true);
  });

  test("adds ready class via fallback timer if fonts API is unavailable", async () => {
    mockDocumentFonts(undefined);

    await loadIconFontReady();

    assert.strictEqual(document.body.classList.contains("icon-font-ready"), true);
  });

  test("does not throw if document.body is not present", async () => {
    const originalBody = dom.window.document.body;
    Object.defineProperty(dom.window.document, "body", {
      value: null,
      writable: true,
      configurable: true,
    });

    await loadIconFontReady();

    Object.defineProperty(dom.window.document, "body", {
      value: originalBody,
      writable: true,
      configurable: true,
    });
  });

  test("uses fallback timer if font loading takes too long", async () => {
    mockDocumentFonts({
      check: () => false,
      load: () => new Promise(() => {}),
      ready: new Promise(() => {}),
    });

    await loadIconFontReady();

    assert.strictEqual(document.body.classList.contains("icon-font-ready"), false);

    // Trigger manual timers
    activeTimers.forEach(t => t.cb());

    assert.strictEqual(document.body.classList.contains("icon-font-ready"), true);
  });

  test("adds ready class when document.readyState is loading", async () => {
    const originalReadyState = dom.window.document.readyState;

    Object.defineProperty(dom.window.document, "readyState", {
      value: "loading",
      writable: true,
      configurable: true,
    });

    mockDocumentFonts({
      check: () => true,
    });

    await loadIconFontReady();

    assert.strictEqual(document.body.classList.contains("icon-font-ready"), false);

    dom.window.document.dispatchEvent(new dom.window.Event("DOMContentLoaded"));

    assert.strictEqual(document.body.classList.contains("icon-font-ready"), true);

    Object.defineProperty(dom.window.document, "readyState", {
      value: originalReadyState,
      writable: true,
      configurable: true,
    });
  });
});
