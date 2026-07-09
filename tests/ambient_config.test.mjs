import test, { describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import { JSDOM } from "jsdom";

describe("Ambient Config", () => {
  let dom;
  let originalConsoleWarn;

  beforeEach(() => {
    dom = new JSDOM("<!DOCTYPE html><html><body></body></html>");
    globalThis.window = dom.window;
    globalThis.document = dom.window.document;
    originalConsoleWarn = globalThis.console.warn;
    delete dom.window.AMBIENT_CONFIG;
  });

  afterEach(() => {
    globalThis.console.warn = originalConsoleWarn;
    delete globalThis.window;
    delete globalThis.document;
  });

  test("should set default AMBIENT_CONFIG if none exists", async () => {
    await import(`../js/ambient/config.js?t=${Date.now()}`);
    assert.deepStrictEqual(dom.window.AMBIENT_CONFIG, {
      enabled: true,
      minWidth: 1024,
      maxParticles: 300,
      densityDivisor: 20000,
      radius: { min: 1.0, max: 8.0 },
      alpha: { min: 0.1, max: 0.6 },
      speed: 0.6,
      zIndex: 1,
      blend: "screen",
      respectReducedMotion: false,
    });
  });

  test("should merge with existing AMBIENT_CONFIG", async () => {
    dom.window.AMBIENT_CONFIG = { enabled: false, maxParticles: 100 };
    await import(`../js/ambient/config.js?t=${Date.now()}`);
    assert.strictEqual(dom.window.AMBIENT_CONFIG.enabled, false);
    assert.strictEqual(dom.window.AMBIENT_CONFIG.maxParticles, 100);
    assert.strictEqual(dom.window.AMBIENT_CONFIG.minWidth, 1024);
  });

  test("should catch errors and log a warning", async () => {
    let warnArgs = null;
    globalThis.console.warn = (...args) => {
      warnArgs = args;
    };

    const originalAssign = Object.assign;
    Object.assign = () => {
      throw new Error("mock error");
    };

    try {
      await import(`../js/ambient/config.js?t=${Date.now()}`);
    } finally {
      Object.assign = originalAssign;
    }

    assert.ok(warnArgs);
    assert.strictEqual(warnArgs[0], "Caught exception initializing ambient config:");
    assert.ok(warnArgs[1] instanceof Error);
    assert.strictEqual(warnArgs[1].message, "mock error");
  });
});
