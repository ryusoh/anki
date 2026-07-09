import test, { describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import { JSDOM } from "jsdom";
import fs from "node:fs";

describe("Image Fallback Loader", () => {
  let dom;
  let originalConsoleWarn;

  beforeEach(() => {
    dom = new JSDOM("<!DOCTYPE html><html><body></body></html>", { url: "http://localhost" });
    globalThis.window = dom.window;
    globalThis.document = dom.window.document;
    originalConsoleWarn = globalThis.console.warn;
    globalThis.console.warn = () => {};
  });

  afterEach(() => {
    globalThis.console.warn = originalConsoleWarn;
    delete globalThis.window;
    delete globalThis.document;
  });

  async function loadScript() {
    await import(`../js/loader/imageFallback.js?t=${Date.now()}`);
  }

  test("should ignore elements without data-fallbacks", async () => {
    const img = document.createElement("img");
    img.src = "test.jpg";
    document.body.appendChild(img);

    await loadScript();

    assert.ok(img.src.includes("test.jpg"));
    assert.strictEqual(img.classList.contains("is-fallback-ready"), false);
  });

  test("should handle invalid JSON gracefully and warn", async () => {
    let warnCalled = false;
    globalThis.console.warn = () => { warnCalled = true; };

    const img = document.createElement("img");
    img.setAttribute("data-fallbacks", "invalid json");
    document.body.appendChild(img);

    await loadScript();

    assert.ok(warnCalled);
    assert.strictEqual(img.classList.contains("is-fallback-ready"), false);
  });

  test("should do nothing if parsed list is not an array or is empty", async () => {
    const img1 = document.createElement("img");
    img1.setAttribute("data-fallbacks", "{}");
    const img2 = document.createElement("img");
    img2.setAttribute("data-fallbacks", "[]");
    document.body.appendChild(img1);
    document.body.appendChild(img2);

    await loadScript();

    assert.strictEqual(img1.classList.contains("is-fallback-ready"), false);
    assert.strictEqual(img2.classList.contains("is-fallback-ready"), false);
    assert.strictEqual(img1.src, "");
    assert.strictEqual(img2.src, "");
  });

  test("should set src to the first fallback URL if src is empty", async () => {
    const img = document.createElement("img");
    img.setAttribute("data-fallbacks", '["fallback.jpg"]');
    document.body.appendChild(img);

    await loadScript();

    assert.ok(img.src.includes("fallback.jpg"));
  });

  test("should set src to the first fallback URL if src is different", async () => {
    const img = document.createElement("img");
    img.src = "other.jpg";
    img.setAttribute("data-fallbacks", '["fallback.jpg"]');
    document.body.appendChild(img);

    await loadScript();

    assert.ok(img.src.includes("fallback.jpg"));
  });

  test("should add is-fallback-ready class immediately if already complete", async () => {
    const img = document.createElement("img");
    const fullPath = "http://localhost/fallback.jpg";
    img.setAttribute("data-fallbacks", `["${fullPath}"]`);

    Object.defineProperty(img, "complete", { value: true, configurable: true });
    Object.defineProperty(img, "naturalWidth", { value: 100, configurable: true });
    img.src = fullPath;
    document.body.appendChild(img);

    await loadScript();

    assert.strictEqual(img.classList.contains("is-fallback-ready"), true);
  });

  test("should add is-fallback-ready class on successful load", async () => {
    const img = document.createElement("img");
    img.setAttribute("data-fallbacks", '["fallback.jpg"]');
    document.body.appendChild(img);

    await loadScript();

    img.dispatchEvent(new dom.window.Event("load"));

    assert.strictEqual(img.classList.contains("is-fallback-ready"), true);
  });

  test("should advance to next URL on error", async () => {
    const img = document.createElement("img");
    const fail1 = "http://localhost/fail1.jpg";
    const fail2 = "http://localhost/fail2.jpg";
    const success = "http://localhost/success.jpg";
    img.setAttribute("data-fallbacks", `["${fail1}", "${fail2}", "${success}"]`);
    document.body.appendChild(img);

    await loadScript();

    assert.ok(img.src.includes("fail1.jpg"));

    img.dispatchEvent(new dom.window.Event("error"));
    assert.ok(img.src.includes("fail1.jpg"));

    img.dispatchEvent(new dom.window.Event("error"));
    assert.ok(img.src.includes("fail2.jpg"));

    img.dispatchEvent(new dom.window.Event("error"));
    assert.ok(img.src.includes("success.jpg"));

    img.dispatchEvent(new dom.window.Event("error"));
    assert.ok(img.src.includes("success.jpg"));
  });

  test("should catch global execution errors and warn", async () => {
    let warnCalled = false;
    globalThis.console.warn = () => { warnCalled = true; };

    const originalQuerySelectorAll = dom.window.document.querySelectorAll;
    dom.window.document.querySelectorAll = () => {
      throw new Error("Test execution error");
    };

    await loadScript();

    assert.ok(warnCalled);

    dom.window.document.querySelectorAll = originalQuerySelectorAll;
  });
});
