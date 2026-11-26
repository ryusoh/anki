import test, { describe, beforeEach } from "node:test";
import assert from "node:assert";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { JSDOM } from "jsdom";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const GOVERNOR_JS = fs.readFileSync(
  path.join(__dirname, "../background_cpu_governor/web/governor.js"),
  "utf8",
);

describe("background_cpu_governor/web/governor.js", () => {
  let dom;
  let nativeRafCalls;
  let nativeCancelled;
  let nextNativeId;

  function loadGovernor(config = {}) {
    dom.window.__ankiCpuGovernorConfig = config;
    dom.window.eval(GOVERNOR_JS);
    return dom.window.__ankiCpuGovernor;
  }

  beforeEach(() => {
    dom = new JSDOM("<!DOCTYPE html><html><head></head><body></body></html>", {
      url: "http://localhost",
      runScripts: "dangerously",
    });
    Object.defineProperty(dom.window.document, "hidden", {
      configurable: true,
      get: () => false,
    });
    nativeRafCalls = [];
    nativeCancelled = [];
    nextNativeId = 100;
    dom.window.requestAnimationFrame = (cb) => {
      const id = nextNativeId++;
      nativeRafCalls.push({ id, cb });
      return id;
    };
    dom.window.cancelAnimationFrame = (id) => {
      nativeCancelled.push(id);
    };
  });

  test("forwards rAF natively while active and queues/cancels/flushes around pause", () => {
    const gov = loadGovernor({ enabled: true });
    assert.strictEqual(gov.isPaused(), false);

    const events = [];
    dom.window.addEventListener("anki-cpu-governor-change", (e) => {
      events.push(e.detail.paused);
    });

    const idActive = dom.window.requestAnimationFrame(() => {});
    assert.strictEqual(idActive, 100);
    assert.strictEqual(nativeRafCalls.length, 1);

    gov.setPaused(true);
    assert.strictEqual(gov.isPaused(), true);
    assert.deepStrictEqual(events, [true]);
    assert.ok(
      dom.window.document.documentElement.classList.contains(
        "anki-cpu-governor-paused",
      ),
    );
    assert.strictEqual(
      dom.window.document.documentElement.dataset.cpuGovernorPaused,
      "1",
    );
    const styleEl = dom.window.document.getElementById(
      "anki-cpu-governor-style",
    );
    assert.ok(styleEl.textContent.includes("animation-play-state: paused"));

    const queued1 = dom.window.requestAnimationFrame(() => {});
    const queued2 = dom.window.requestAnimationFrame(() => {});
    assert.ok(queued1 < 0 && queued2 < 0);
    assert.strictEqual(nativeRafCalls.length, 1);
    assert.strictEqual(gov.getPendingCount(), 2);

    dom.window.cancelAnimationFrame(queued1);
    assert.strictEqual(gov.getPendingCount(), 1);
    assert.strictEqual(nativeCancelled.length, 0);

    dom.window.cancelAnimationFrame(idActive);
    assert.deepStrictEqual(nativeCancelled, [idActive]);

    gov.setPaused(false);
    assert.strictEqual(gov.isPaused(), false);
    assert.deepStrictEqual(events, [true, false]);
    assert.strictEqual(gov.getPendingCount(), 0);
    assert.strictEqual(nativeRafCalls.length, 2);
  });

  test("visibilitychange and setEnabled(false) control pause state cleanly", () => {
    const gov = loadGovernor({
      enabled: true,
      pauseCssAnimations: false,
      pauseRaf: true,
    });

    let hiddenState = true;
    Object.defineProperty(dom.window.document, "hidden", {
      configurable: true,
      get: () => hiddenState,
    });
    dom.window.document.dispatchEvent(new dom.window.Event("visibilitychange"));
    assert.strictEqual(gov.isPaused(), true);
    assert.strictEqual(
      dom.window.document.getElementById("anki-cpu-governor-style"),
      null,
    );

    dom.window.requestAnimationFrame(() => {});
    assert.strictEqual(gov.getPendingCount(), 1);

    gov.setEnabled(false);
    assert.strictEqual(gov.isPaused(), false);
    assert.strictEqual(gov.getPendingCount(), 0);
    assert.strictEqual(nativeRafCalls.length, 1);

    hiddenState = false;
    gov.setEnabled(true);
    dom.window.document.dispatchEvent(new dom.window.Event("visibilitychange"));
    assert.strictEqual(gov.isPaused(), false);
  });
});
