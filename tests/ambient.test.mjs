import test, { describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import { JSDOM } from "jsdom";

describe("Ambient Logic", () => {
  let dom;
  let originalConsoleWarn;
  let sketchCreateConfig = null;
  let sketchInstance = null;

  function initSketchMock(domWindow) {
    sketchCreateConfig = null;
    sketchInstance = null;
    domWindow.Sketch = {
      create: (config) => {
        sketchCreateConfig = config;
        sketchInstance = {
          ...config,
          width: 1920,
          height: 1080,
          canvas: {
            style: {},
            className: "",
          },
          start: () => {},
          stop: () => {},
          clear: () => {},
          save: () => {},
          restore: () => {},
          beginPath: () => {},
          arc: () => {},
          fill: () => {},
          fillRect: () => {},
        };
        return sketchInstance;
      },
    };
  }

  beforeEach(() => {
    originalConsoleWarn = globalThis.console.warn;
    globalThis.console.warn = () => {};
  });

  afterEach(() => {
    globalThis.console.warn = originalConsoleWarn;
    delete globalThis.window;
    delete globalThis.document;
    delete globalThis.matchMedia;
    sketchCreateConfig = null;
    sketchInstance = null;
  });

  async function loadAmbient(url = "http://localhost") {
    dom = new JSDOM("<!DOCTYPE html><html><body><div id='appContent'></div></body></html>", { url });
    globalThis.window = dom.window;
    globalThis.document = dom.window.document;
    globalThis.matchMedia = () => ({ matches: false });
    dom.window.matchMedia = () => ({ matches: false });

    Object.defineProperty(dom.window, "innerWidth", {
      writable: true,
      configurable: true,
      value: 1200,
    });

    initSketchMock(dom.window);

    dom.window.AMBIENT_CONFIG = {
      enabled: true,
      minWidth: 1024,
      maxParticles: 10,
      densityDivisor: 20000,
      radius: { min: 1.0, max: 8.0 },
      alpha: { min: 0.1, max: 0.6 },
      speed: 0.6,
      zIndex: 1,
      blend: "screen",
      respectReducedMotion: false,
    };

    await import(`../js/ambient/ambient.js?t=${Date.now()}`);
  }

  test("should initialize Sketch when conditions are met", async () => {
    await loadAmbient();
    assert.ok(sketchCreateConfig);
    assert.ok(sketchInstance);
  });

  test("should not initialize if not enabled", async () => {
    // Modify AMBIENT_CONFIG before import
    dom = new JSDOM("<!DOCTYPE html><html><body></body></html>", { url: "http://localhost" });
    globalThis.window = dom.window;
    globalThis.document = dom.window.document;
    initSketchMock(dom.window);
    dom.window.AMBIENT_CONFIG = { enabled: false, minWidth: 1024 };

    await import(`../js/ambient/ambient.js?t=${Date.now()}`);
    assert.strictEqual(sketchCreateConfig, null);
  });

  test("should initialize with debug settings", async () => {
    await loadAmbient("http://localhost?ambient=debug");
    assert.ok(sketchCreateConfig);
    assert.strictEqual(sketchInstance.canvas.style.zIndex, "999");
  });

  test("should abort if window innerWidth is less than minWidth", async () => {
    dom = new JSDOM("<!DOCTYPE html><html><body></body></html>", { url: "http://localhost" });
    globalThis.window = dom.window;
    globalThis.document = dom.window.document;
    initSketchMock(dom.window);
    dom.window.AMBIENT_CONFIG = { enabled: true, minWidth: 1024 };
    Object.defineProperty(dom.window, "innerWidth", {
      writable: true,
      configurable: true,
      value: 800,
    });

    await import(`../js/ambient/ambient.js?t=${Date.now()}`);
    assert.strictEqual(sketchCreateConfig, null);
  });

  test("should abort if prefers reduced motion is true and respectReducedMotion is true", async () => {
    dom = new JSDOM("<!DOCTYPE html><html><body></body></html>", { url: "http://localhost" });
    globalThis.window = dom.window;
    globalThis.document = dom.window.document;
    globalThis.matchMedia = () => ({ matches: true });
    dom.window.matchMedia = () => ({ matches: true });
    initSketchMock(dom.window);
    dom.window.AMBIENT_CONFIG = { enabled: true, minWidth: 1024, respectReducedMotion: true };

    await import(`../js/ambient/ambient.js?t=${Date.now()}`);
    assert.strictEqual(sketchCreateConfig, null);
  });

  test("should initialize even if prefers reduced motion is true but respectReducedMotion is false", async () => {
    dom = new JSDOM("<!DOCTYPE html><html><body></body></html>", { url: "http://localhost" });
    globalThis.window = dom.window;
    globalThis.document = dom.window.document;
    globalThis.matchMedia = () => ({ matches: true });
    dom.window.matchMedia = () => ({ matches: true });
    initSketchMock(dom.window);
    dom.window.AMBIENT_CONFIG = { enabled: true, minWidth: 1024, respectReducedMotion: false };

    await import(`../js/ambient/ambient.js?t=${Date.now()}`);
    assert.ok(sketchCreateConfig);
  });

  test("should execute Sketch setup, update, draw, and resize methods", async () => {
    await loadAmbient("http://localhost?ambient=trace");
    assert.ok(sketchInstance);

    assert.ok(sketchInstance.setup);
    sketchInstance.setup();

    assert.ok(sketchInstance.resize);
    sketchInstance.resize();

    assert.ok(sketchInstance.update);
    sketchInstance.update();

    assert.ok(sketchInstance.draw);
    let fillRectCalled = false;
    let arcCalled = false;
    let fillCalled = false;
    sketchInstance.fillRect = () => { fillRectCalled = true; };
    sketchInstance.arc = () => { arcCalled = true; };
    sketchInstance.fill = () => { fillCalled = true; };

    // With trace=true and particles set up, draw will paint particles.
    // Let's call draw.
    sketchInstance.draw.call(sketchInstance);
    assert.ok(arcCalled);
    assert.ok(fillCalled);
  });

  test("should catch exceptions and log warning", async () => {
    let warnCalled = false;
    globalThis.console.warn = () => { warnCalled = true; };

    dom = new JSDOM("<!DOCTYPE html><html><body></body></html>", { url: "http://localhost" });
    globalThis.window = dom.window;
    globalThis.document = dom.window.document;
    initSketchMock(dom.window);
    dom.window.AMBIENT_CONFIG = { enabled: true, minWidth: 1024 };

    dom.window.matchMedia = () => {
      throw new Error("mock matchMedia error");
    };
    globalThis.matchMedia = dom.window.matchMedia;

    await import(`../js/ambient/ambient.js?t=${Date.now()}`);
    assert.ok(warnCalled);
  });
});
