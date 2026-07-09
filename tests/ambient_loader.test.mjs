import test, { describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import { JSDOM } from "jsdom";

describe("Ambient Loader", () => {
  let dom;
  let originalConsoleWarn;
  let appendCalls = [];

  beforeEach(() => {
    dom = new JSDOM("<!DOCTYPE html><html><head></head><body></body></html>", { url: "http://localhost" });
    globalThis.window = dom.window;
    globalThis.document = dom.window.document;
    originalConsoleWarn = globalThis.console.warn;
    globalThis.console.warn = () => {};

    appendCalls = [];
    const originalAppend = dom.window.document.head.appendChild;
    dom.window.document.head.appendChild = (el) => {
      appendCalls.push(el);
      return originalAppend.call(dom.window.document.head, el);
    };

    globalThis.matchMedia = () => ({ matches: false });
    dom.window.matchMedia = () => ({ matches: false });

    Object.defineProperty(dom.window, "innerWidth", {
      writable: true,
      configurable: true,
      value: 1024,
    });
  });

  afterEach(() => {
    globalThis.console.warn = originalConsoleWarn;
    delete globalThis.window;
    delete globalThis.document;
    delete globalThis.matchMedia;
  });

  test("should abort if prefers-reduced-motion is true", async () => {
    dom.window.matchMedia = (query) => ({
      matches: query === "(prefers-reduced-motion: reduce)",
    });

    await import(`../js/ambient/loader.js?t=${Date.now()}`);

    assert.strictEqual(appendCalls.length, 0);
  });

  test("should abort if window innerWidth is less than 1024", async () => {
    dom.window.innerWidth = 800;

    await import(`../js/ambient/loader.js?t=${Date.now()}`);

    assert.strictEqual(appendCalls.length, 0);
  });

  test("should load CSS and scripts if conditions are met", async () => {
    await import(`../js/ambient/loader.js?t=${Date.now()}`);

    assert.ok(appendCalls.length > 0);

    const link = appendCalls.find((el) => el.tagName === "LINK");
    assert.ok(link);
    assert.strictEqual(link.href, "http://localhost/css/ambient/ambient.css");

    const script = appendCalls.find((el) => el.tagName === "SCRIPT");
    assert.ok(script);
    assert.strictEqual(script.src, "http://localhost/js/ambient/sketch.js");
  });

  test("should handle document head append error", async () => {
    let warnArgs = null;
    globalThis.console.warn = (...args) => {
      warnArgs = args;
    };

    dom.window.document.head.appendChild = () => {
      throw new Error("mock DOM error");
    };

    await import(`../js/ambient/loader.js?t=${Date.now()}`);

    assert.ok(warnArgs);
    assert.strictEqual(warnArgs[0], "Caught exception initializing ambient loader:");
    assert.ok(warnArgs[1] instanceof Error);
    assert.strictEqual(warnArgs[1].message, "mock DOM error");
  });
});
