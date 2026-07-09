import test, { describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import { JSDOM } from "jsdom";

describe("quantum_shader fallback", () => {
  let dom;
  let originalConsoleError;

  beforeEach(() => {
    dom = new JSDOM("<!DOCTYPE html><html><body><div id='appContent'></div></body></html>", { url: "http://localhost" });
    globalThis.window = dom.window;
    globalThis.document = dom.window.document;
    originalConsoleError = globalThis.console.error;
    globalThis.console.error = () => {};

    globalThis.requestAnimationFrame = (cb) => setTimeout(cb, 0);
    globalThis.cancelAnimationFrame = (id) => clearTimeout(id);
    dom.window.requestAnimationFrame = globalThis.requestAnimationFrame;
    dom.window.cancelAnimationFrame = globalThis.cancelAnimationFrame;

    const originalCreateElement = dom.window.document.createElement.bind(dom.window.document);
    dom.window.document.createElement = (tagName) => {
      const el = originalCreateElement(tagName);
      if (tagName === "canvas") {
        el.width = 100;
        el.height = 100;
        el.getContext = () => ({
          createImageData: () => ({
            data: new Uint8ClampedArray(40000),
          }),
          putImageData: () => {},
          fillRect: () => {},
          clearRect: () => {},
          fill: () => {},
          beginPath: () => {},
        });
      }
      return el;
    };

    dom.window.ResizeObserver = class {
      observe() {}
      unobserve() {}
      disconnect() {}
    };
    globalThis.ResizeObserver = dom.window.ResizeObserver;
  });

  afterEach(() => {
    globalThis.console.error = originalConsoleError;
    delete globalThis.window;
    delete globalThis.document;
    delete globalThis.ResizeObserver;
  });

  test("initializes and triggers offline fallback without three.js", async () => {
    Object.defineProperty(document, "readyState", {
      value: "complete",
      configurable: true,
    });

    await import(`../js/ambient/quantum_shader.js?t=${Date.now()}`);

    await new Promise((resolve) => setTimeout(resolve, 50));

    const offlineFallback = document.querySelector(".quantum-offline");
    assert.ok(offlineFallback);
  });
});
