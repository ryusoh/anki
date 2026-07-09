import test, { describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import { JSDOM } from "jsdom";

describe("Marquee", () => {
  let dom;
  let MARQUEE_CONFIG;
  let gsapToCalls = [];
  let tickerCallbacks = [];

  beforeEach(async () => {
    dom = new JSDOM("<!DOCTYPE html><html><body></body></html>", { url: "http://localhost" });
    globalThis.window = dom.window;
    globalThis.document = dom.window.document;

    gsapToCalls = [];
    tickerCallbacks = [];

    dom.window.gsap = {
      to: (el, opts) => {
        gsapToCalls.push({ el, opts });
      },
      utils: {
        wrap: (min, max) => (val) => val,
      },
      ticker: {
        add: (cb) => {
          tickerCallbacks.push(cb);
        },
      },
    };
    globalThis.window.gsap = dom.window.gsap;

    delete dom.window.ontouchstart;
    Object.defineProperty(globalThis.navigator, "maxTouchPoints", {
      value: 0,
      configurable: true,
      writable: true,
    });

    // Dynamically import config after global DOM is set up
    const configMod = await import("../js/config.js");
    MARQUEE_CONFIG = configMod.MARQUEE_CONFIG;
    MARQUEE_CONFIG.enabled = true;
  });

  afterEach(() => {
    delete globalThis.window;
    delete globalThis.document;
  });

  async function loadMarquee() {
    await import(`../js/ui/marquee.js?t=${Date.now()}`);
  }

  test("should do nothing if gsap is not defined", async () => {
    delete dom.window.gsap;
    await loadMarquee();
    assert.strictEqual(document.querySelectorAll(".marquee-container").length, 0);
  });

  test("should do nothing if touch device", async () => {
    dom.window.ontouchstart = () => {};
    Object.defineProperty(globalThis.navigator, "maxTouchPoints", {
      value: 5,
      configurable: true,
    });

    await loadMarquee();
    assert.strictEqual(gsapToCalls.length, 0);
  });

  test("should do nothing if MARQUEE_CONFIG is not enabled", async () => {
    MARQUEE_CONFIG.enabled = false;

    await loadMarquee();
    assert.strictEqual(gsapToCalls.length, 0);

    MARQUEE_CONFIG.enabled = true;
  });

  test("should initialize marquee without widget", async () => {
    document.body.innerHTML = `
      <div class="marquee-container marquee-right">
        <div class="marquee-content">
          <span>Test</span>
        </div>
      </div>
    `;

    await loadMarquee();

    assert.ok(gsapToCalls.length > 0);
    const wrapper = document.querySelector(".marquee-container");
    assert.strictEqual(wrapper.children.length, 2);
  });

  test("should handle undefined config options", async () => {
    const oldSize = MARQUEE_CONFIG.sizeMultiplier;
    const oldDir = MARQUEE_CONFIG.direction;
    const oldDur = MARQUEE_CONFIG.animationDuration;

    MARQUEE_CONFIG.sizeMultiplier = undefined;
    MARQUEE_CONFIG.direction = undefined;
    MARQUEE_CONFIG.animationDuration = undefined;

    document.body.innerHTML = `
      <div class="marquee-container marquee-right">
        <div class="marquee-content">
          <span>Test</span>
        </div>
      </div>
    `;

    await loadMarquee();

    const call = gsapToCalls[0];
    assert.ok(call);
    assert.strictEqual(call.opts.duration, 20);

    MARQUEE_CONFIG.sizeMultiplier = oldSize;
    MARQUEE_CONFIG.direction = oldDir;
    MARQUEE_CONFIG.animationDuration = oldDur;
  });

  test("should split into chars and init gravity with widget", async () => {
    document.body.innerHTML = `
      <div class="quantum-widget" style="width: 100px; height: 100px;"></div>
      <div class="marquee-container marquee-right">
        <div class="marquee-content">
          <span>A B</span>
        </div>
      </div>
      <div class="marquee-container">
        <div class="marquee-content">
          <span>C D</span>
        </div>
      </div>
    `;

    // Mock getBoundingClientRect
    dom.window.Element.prototype.getBoundingClientRect = () => ({
      width: 100,
      height: 100,
      top: 0,
      left: 0,
      bottom: 100,
      right: 100,
    });

    await loadMarquee();

    assert.ok(tickerCallbacks.length > 0);
    // trigger ticker
    tickerCallbacks[0]();
  });

  test("should handle multiplier", async () => {
    MARQUEE_CONFIG.sizeMultiplier = 1.5;
    document.body.innerHTML = `
      <div class="marquee-container">
        <div class="marquee-content">
          <span>Test</span>
        </div>
      </div>
    `;

    await loadMarquee();

    const content = document.querySelector(".marquee-content");
    assert.strictEqual(content.style.fontSize, "150%");

    MARQUEE_CONFIG.sizeMultiplier = 1;
  });

  test("should trigger gravity loop with zero width widget", async () => {
    document.body.innerHTML = `
      <div class="quantum-widget" style="width: 0px; height: 0px;"></div>
      <div class="marquee-container">
        <div class="marquee-content">
          <span>A B</span>
        </div>
      </div>
    `;

    dom.window.Element.prototype.getBoundingClientRect = () => ({
      width: 0,
      height: 0,
      top: 0,
      left: 0,
      bottom: 0,
      right: 0,
    });

    await loadMarquee();

    assert.ok(tickerCallbacks.length > 0);
    tickerCallbacks[0]();
  });

  test("should skip chars that are far away from widget", async () => {
    document.body.innerHTML = `
      <div class="quantum-widget" style="width: 10px; height: 10px;"></div>
      <div class="marquee-container">
        <div class="marquee-content">
          <span>A</span>
        </div>
      </div>
    `;

    let callCount = 0;
    dom.window.Element.prototype.getBoundingClientRect = function () {
      callCount++;
      if (callCount === 1) {
        return { width: 10, height: 10, top: 0, left: 0, bottom: 10, right: 10 };
      }
      return { width: 10, height: 10, top: 1000, left: 1000, bottom: 1010, right: 1010 };
    };

    await loadMarquee();

    assert.ok(tickerCallbacks.length > 0);
    const tickerCallback = tickerCallbacks[0];
    tickerCallback();

    const span = document.querySelector(".mq-char");
    assert.ok(span);
    span.style.transform = "scale(2)";
    span.style.marginLeft = "10px";
    span.style.marginRight = "10px";

    callCount = 0;
    tickerCallback();

    assert.strictEqual(span.style.transform, "");
    assert.strictEqual(span.style.marginLeft, "");
    assert.strictEqual(span.style.marginRight, "");
  });

  test("should handle zero distance calculation inside ticker", async () => {
    document.body.innerHTML = `
      <div class="quantum-widget" style="width: 100px; height: 100px;"></div>
      <div class="marquee-container">
        <div class="marquee-content">
          <span>A</span>
        </div>
      </div>
    `;

    let callCount = 0;
    dom.window.Element.prototype.getBoundingClientRect = function () {
      callCount++;
      if (callCount === 1) {
        return { left: 0, top: 0, width: 100, height: 100, right: 100, bottom: 100 };
      }
      return { left: 45, top: 45, width: 10, height: 10, right: 55, bottom: 55 };
    };

    await loadMarquee();

    assert.ok(tickerCallbacks.length > 0);
    tickerCallbacks[0]();

    const char = document.querySelector(".mq-char");
    assert.strictEqual(char.style.transform, "");
  });

  test("should apply gravity transforms when chars approach the widget", async () => {
    document.body.innerHTML = `
      <div class="quantum-widget" style="width: 10px; height: 10px;"></div>
      <div class="marquee-container marquee-right">
        <div class="marquee-content">
          <span>A</span>
        </div>
      </div>
    `;

    let callCount = 0;
    dom.window.Element.prototype.getBoundingClientRect = function () {
      callCount++;
      if (callCount === 1) {
        return { width: 10, height: 10, top: 0, left: 0, right: 10, bottom: 10 };
      }
      return { width: 10, height: 10, top: 0, left: -50, right: -40, bottom: 10 };
    };

    await loadMarquee();

    assert.ok(tickerCallbacks.length > 0);
    tickerCallbacks[0]();

    const span = document.querySelector(".mq-char");
    assert.ok(span.style.transform !== "");
    assert.ok(span.style.marginLeft !== "");
  });

  test("should bind DOMContentLoaded if readyState is loading", async () => {
    const originalReadyState = dom.window.document.readyState;
    Object.defineProperty(dom.window.document, "readyState", {
      value: "loading",
      configurable: true,
    });

    let addedListener = null;
    let addedHandler = null;
    dom.window.document.addEventListener = (event, handler) => {
      addedListener = event;
      addedHandler = handler;
    };

    await loadMarquee();

    assert.strictEqual(addedListener, "DOMContentLoaded");
    assert.ok(addedHandler);

    Object.defineProperty(dom.window.document, "readyState", {
      value: originalReadyState,
      configurable: true,
    });
  });
});
