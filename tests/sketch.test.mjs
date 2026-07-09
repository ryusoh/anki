import test, { describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import { JSDOM } from "jsdom";

describe("Sketch library", () => {
  let dom;
  let originalSetTimeout;
  let mockContext;
  let Sketch;
  let activeTimers = [];

  beforeEach(async () => {
    dom = new JSDOM("<!DOCTYPE html><html><body></body></html>", { url: "http://localhost" });
    globalThis.window = dom.window;
    globalThis.document = dom.window.document;

    activeTimers = [];
    originalSetTimeout = globalThis.setTimeout;
    globalThis.setTimeout = (cb, delay) => {
      const id = originalSetTimeout(cb, delay);
      activeTimers.push(id);
      return id;
    };
    dom.window.setTimeout = globalThis.setTimeout;

    const originalCreateElement = dom.window.document.createElement.bind(dom.window.document);
    dom.window.document.createElement = (tagName) => {
      const el = originalCreateElement(tagName);
      if (tagName === "canvas") {
        mockContext = {
          canvas: el,
          clearRect: () => {},
          fillRect: () => {},
          save: () => {},
          restore: () => {},
          scale: () => {},
          beginPath: () => {},
        };
        el.getContext = (type) => {
          if (type === "2d" || type === "webgl") {
            return mockContext;
          }
          return null;
        };
      }
      return el;
    };

    // Load sketch
    await import(`../js/ambient/sketch.js?t=${Date.now()}`);
    Sketch = dom.window.Sketch;
  });

  afterEach(() => {
    activeTimers.forEach((id) => clearTimeout(id));
    activeTimers = [];
    globalThis.setTimeout = originalSetTimeout;
    delete globalThis.window;
    delete globalThis.document;
  });

  test("creates a 2d sketch context and exercises lifecycle events", async () => {
    let setupCalled = false;
    let updateCalled = false;
    let drawCalled = false;
    let resizeCalled = false;
    let clickCalled = false;

    const ctx = Sketch.create({
      type: Sketch.CANVAS,
      autostart: true,
      globals: true,
      setup: () => { setupCalled = true; },
      update: () => { updateCalled = true; },
      draw: () => { drawCalled = true; },
      resize: () => { resizeCalled = true; },
      click: () => { clickCalled = true; },
      retina: true,
      autoclear: true,
    });

    assert.ok(ctx);

    // Wait for the RAF loop to invoke update/draw
    await new Promise((r) => originalSetTimeout(r, 20));

    assert.ok(setupCalled);
    assert.ok(resizeCalled);
    assert.ok(updateCalled);
    assert.ok(drawCalled);

    // Stop and toggle
    ctx.stop();
    ctx.toggle();
    assert.strictEqual(ctx.running, true);

    // Trigger resize on window
    dom.window.dispatchEvent(new dom.window.Event("resize"));

    // Trigger touch events
    const canvas = ctx.canvas;
    canvas.dispatchEvent(new dom.window.TouchEvent("touchstart", {
      touches: [{ pageX: 50, pageY: 50, clientX: 50, clientY: 50 }],
    }));
    canvas.dispatchEvent(new dom.window.TouchEvent("touchmove", {
      touches: [{ pageX: 60, pageY: 60, clientX: 60, clientY: 60 }],
    }));
    canvas.dispatchEvent(new dom.window.TouchEvent("touchend", {
      touches: [],
    }));

    // Mouse and keyboard events
    canvas.dispatchEvent(new dom.window.MouseEvent("mousemove", { clientX: 10, clientY: 10 }));
    canvas.dispatchEvent(new dom.window.MouseEvent("mousedown", { clientX: 10, clientY: 10 }));
    canvas.dispatchEvent(new dom.window.MouseEvent("mouseup", { clientX: 10, clientY: 10 }));
    canvas.dispatchEvent(new dom.window.MouseEvent("click", { clientX: 10, clientY: 10 }));
    assert.ok(clickCalled);

    dom.window.document.dispatchEvent(new dom.window.KeyboardEvent("keydown", { keyCode: 32 }));
    dom.window.document.dispatchEvent(new dom.window.KeyboardEvent("keyup", { keyCode: 32 }));

    dom.window.dispatchEvent(new dom.window.Event("blur"));
    dom.window.dispatchEvent(new dom.window.Event("focus"));

    ctx.destroy();
  });

  test("creates a webgl sketch context", () => {
    const ctx = Sketch.create({
      type: Sketch.WEBGL,
      autostart: false,
      globals: false,
    });
    assert.ok(ctx);
    assert.strictEqual(ctx.running, false);
    ctx.destroy();
  });

  test("creates a dom sketch context", () => {
    const ctx = Sketch.create({
      type: Sketch.DOM,
      autostart: false,
      globals: false,
      fullscreen: false,
      autoresize: true,
    });
    assert.ok(ctx);

    dom.window.dispatchEvent(new dom.window.Event("resize"));

    const parent = dom.window.document.createElement("div");
    parent.appendChild(ctx.element);
    ctx.destroy();
  });

  test("provides globals when requested", () => {
    const ctx = Sketch.create({ type: Sketch.DOM, globals: true, autostart: false });
    assert.ok(dom.window.random);
    assert.ok(dom.window.lerp);
    assert.ok(dom.window.map);

    assert.ok(dom.window.random(1, 10) >= 1);
    assert.ok(dom.window.random([1, 2, 3]));
    assert.ok(dom.window.random(5) <= 5);
    assert.strictEqual(dom.window.lerp(0, 10, 0.5), 5);
    assert.strictEqual(dom.window.map(5, 0, 10, 0, 100), 50);
    ctx.destroy();
  });
});
