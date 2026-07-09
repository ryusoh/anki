import test, { describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { JSDOM } from "jsdom";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const CURSOR_INIT_PATH = path.join(__dirname, "../js/cursor-init.js");
const CURSOR_VENDOR_PATH = path.join(__dirname, "../js/vendor/cursor.js");

const cursorInitContent = fs.readFileSync(CURSOR_INIT_PATH, "utf-8");
const cursorVendorContent = fs.readFileSync(CURSOR_VENDOR_PATH, "utf-8");

describe("Cursor Initialization Timing", () => {
  let dom;

  beforeEach(() => {
    dom = new JSDOM("<!DOCTYPE html><html><body></body></html>", { url: "http://localhost" });
    globalThis.window = dom.window;
    globalThis.document = dom.window.document;
    globalThis.matchMedia = () => ({ matches: false });
    dom.window.matchMedia = () => ({ matches: false });
    globalThis.requestAnimationFrame = (cb) => setTimeout(cb, 0);
    globalThis.cancelAnimationFrame = (id) => clearTimeout(id);
    dom.window.requestAnimationFrame = globalThis.requestAnimationFrame;
    dom.window.cancelAnimationFrame = globalThis.cancelAnimationFrame;
    delete dom.window.ontouchstart;
    if (dom.window.__proto__) {
      delete dom.window.__proto__.ontouchstart;
    }
    delete globalThis.window.gsap;
    delete globalThis.window.cursorInstances;
  });

  afterEach(() => {
    if (globalThis.window && globalThis.window.cursorInstances && globalThis.window.cursorInstances.cursor) {
      try {
        globalThis.window.cursorInstances.cursor.destroy();
      } catch (e) {}
    }
    delete globalThis.window;
    delete globalThis.document;
    delete globalThis.matchMedia;
    delete globalThis.requestAnimationFrame;
    delete globalThis.cancelAnimationFrame;
  });

  describe("cursor-init.js syntax checks", () => {
    test("should wait for DOMContentLoaded before initializing", () => {
      assert.ok(cursorInitContent.includes("DOMContentLoaded"));
    });

    test("should check document.readyState before adding listener", () => {
      assert.ok(cursorInitContent.includes("document.readyState"));
    });

    test("should check for window.gsap availability", () => {
      assert.ok(cursorInitContent.includes("window.gsap"));
    });

    test("should not initialize cursor at module evaluation time", () => {
      const lines = cursorInitContent.split("\n");
      let foundInitCursorCall = false;

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        if (line.includes("initCursor({")) {
          const precedingLines = lines.slice(0, i);
          const hasFunctionBefore = precedingLines.some((l) =>
            l.includes("function")
          );
          foundInitCursorCall = hasFunctionBefore;
          break;
        }
      }
      assert.strictEqual(foundInitCursorCall, true);
    });

    test("should have initCursorOnce or similar wrapped function", () => {
      assert.ok(/function\s+\w*init\w*\s*\(/.test(cursorInitContent));
    });

    test("should handle both loading and complete readyState", () => {
      assert.ok(cursorInitContent.includes('document.readyState === "loading"') || cursorInitContent.includes("document.readyState === 'loading'"));
      assert.ok(cursorInitContent.includes("addEventListener"));
      assert.ok(/else\s*\{/.test(cursorInitContent));
    });

    test("should call initCursorOnce in both branches", () => {
      const initOnceCalls = (cursorInitContent.match(/initCursorOnce\(\)/g) || [])
        .length;
      assert.ok(initOnceCalls >= 2);
    });
  });

  describe("cursor vendor module checks", () => {
    test("initCursor should be exported", () => {
      assert.ok(cursorVendorContent.includes("export function initCursor"));
    });

    test("initCursor should handle missing GSAP gracefully", () => {
      assert.ok(cursorVendorContent.includes("window.gsap"));
    });

    test("CustomCursor should check for touch devices", () => {
      assert.ok(cursorVendorContent.includes("isTouchDevice"));
    });
  });

  describe("cursor-init.js execution", () => {
    test("should initialize cursor when GSAP is available and DOM is ready", async () => {
      window.gsap = {
        registerPlugin: () => {},
        to: () => {},
        timeline: () => {},
        quickSetter: () => () => {},
        utils: { clamp: () => {}, mapRange: () => {} },
      };

      Object.defineProperty(document, "readyState", {
        value: "complete",
        configurable: true,
      });

      await import(`../js/cursor-init.js?t=${Date.now()}`);

      await new Promise((resolve) => setTimeout(resolve, 10));

      assert.ok(window.cursorInstances);
      assert.ok(window.cursorInstances.cursor);
    });

    test("should wait for DOMContentLoaded when document is still loading", async () => {
      window.gsap = {
        registerPlugin: () => {},
        to: () => {},
        timeline: () => {},
        quickSetter: () => () => {},
        utils: { clamp: () => {}, mapRange: () => {} },
      };

      Object.defineProperty(document, "readyState", {
        value: "loading",
        configurable: true,
      });

      await import(`../js/cursor-init.js?t=${Date.now()}`);

      assert.strictEqual(window.cursorInstances, undefined);

      document.dispatchEvent(new window.Event("DOMContentLoaded"));

      await new Promise((resolve) => setTimeout(resolve, 10));

      assert.ok(window.cursorInstances);
      assert.ok(window.cursorInstances.cursor);
    });

    test("should not initialize when GSAP is not available", async () => {
      delete window.gsap;

      Object.defineProperty(document, "readyState", {
        value: "complete",
        configurable: true,
      });

      await import(`../js/cursor-init.js?t=${Date.now()}`);

      await new Promise((resolve) => setTimeout(resolve, 10));

      assert.strictEqual(window.cursorInstances, undefined);
    });
  });
});
