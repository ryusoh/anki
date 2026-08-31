import test, { describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import { JSDOM } from "jsdom";

describe("tilt_effect", () => {
  let dom;
  let TILT_EFFECT;
  let gsapToCalls = [];
  let gsapSetCalls = [];
  let gsapQuickToCalls = [];

  beforeEach(async () => {
    dom = new JSDOM(`
      <!DOCTYPE html>
      <html>
      <body>
        <nav class="container"></nav>
        <div class="quantum-widget"></div>
      </body>
      </html>
    `, { url: "http://localhost" });

    globalThis.window = dom.window;
    globalThis.document = dom.window.document;

    gsapToCalls = [];
    gsapSetCalls = [];
    gsapQuickToCalls = [];

    dom.window.gsap = {
      set: (el, opts) => {
        gsapSetCalls.push({ el, opts });
      },
      to: (el, opts) => {
        gsapToCalls.push({ el, opts });
      },
      quickTo: (el, prop, opts) => {
        return (val) => {
          gsapQuickToCalls.push({ el, prop, opts, val });
        };
      },
    };
    globalThis.window.gsap = dom.window.gsap;

    // Mock requestAnimationFrame
    dom.window.requestAnimationFrame = (cb) => cb();
    globalThis.window.requestAnimationFrame = dom.window.requestAnimationFrame;

    delete dom.window.ontouchstart;
    Object.defineProperty(globalThis.navigator, "maxTouchPoints", {
      value: 0,
      configurable: true,
      writable: true,
    });

    // Mock matchMedia for fine pointer
    dom.window.matchMedia = (query) => ({
      matches: false,
      media: query,
    });

    // Dynamically import config after global DOM is set up
    const configMod = await import("../js/config.js");
    TILT_EFFECT = configMod.TILT_EFFECT;
    TILT_EFFECT.enabled = true;
  });

  afterEach(() => {
    delete globalThis.window;
    delete globalThis.document;
  });

  async function loadScript() {
    await import(`../js/ui/tilt_effect.js?t=${Date.now()}`);
  }

  test("should return early if disabled", async () => {
    TILT_EFFECT.enabled = false;
    await loadScript();
    assert.strictEqual(gsapSetCalls.length, 0);
    TILT_EFFECT.enabled = true;
  });

  test("should return early if no gsap", async () => {
    delete dom.window.gsap;
    await loadScript();
  });

  test("should return early on touch device without fine pointer", async () => {
    dom.window.ontouchstart = () => {};
    Object.defineProperty(globalThis.navigator, "maxTouchPoints", {
      value: 1,
      configurable: true,
    });
    dom.window.matchMedia = () => ({
      matches: false, // pointer: fine is false
    });

    await loadScript();
    assert.strictEqual(gsapSetCalls.length, 0);
  });

  test("should init on touch device if fine pointer is true", async () => {
    dom.window.ontouchstart = () => {};
    Object.defineProperty(globalThis.navigator, "maxTouchPoints", {
      value: 1,
      configurable: true,
    });
    dom.window.matchMedia = () => ({
      matches: true, // pointer: fine is true
    });

    await loadScript();
    assert.ok(gsapSetCalls.length > 0);
  });

  test("should attach event listeners and calculate rotation on mousemove", async () => {
    await loadScript();

    const container = document.querySelector(".quantum-widget");
    assert.ok(container);

    container.getBoundingClientRect = () => ({
      left: 100,
      top: 100,
      width: 200,
      height: 200,
    });

    // Mouseenter cached rect
    container.dispatchEvent(new dom.window.MouseEvent("mouseenter"));

    const event = new dom.window.MouseEvent("mousemove", {
      clientX: 150,
      clientY: 150,
    });
    Object.defineProperty(event, "pageX", { value: 150 });
    Object.defineProperty(event, "pageY", { value: 150 });
    container.dispatchEvent(event);

    assert.ok(gsapQuickToCalls.length > 0);
    const xCall = gsapQuickToCalls.find(c => c.el === container && c.prop === "rotateX");
    const yCall = gsapQuickToCalls.find(c => c.el === container && c.prop === "rotateY");
    assert.ok(xCall);
    assert.ok(yCall);
    // centerX = 200/2 = 100, pageX - left = 150 - 100 = 50.
    // centerY = 200/2 = 100, pageY - top = 150 - 100 = 50.
    // rotateX = ((50 - 100) / 100) * -10 = 5.
    // rotateY = ((50 - 100) / 100) * 10 = -5.
    assert.strictEqual(xCall.val, 5);
    assert.strictEqual(yCall.val, -5);
  });

  test("should reset rotation on mouseleave", async () => {
    await loadScript();

    const container = document.querySelector(".quantum-widget");
    assert.ok(container);

    container.dispatchEvent(new dom.window.MouseEvent("mouseleave"));

    assert.ok(gsapToCalls.length > 0);
    const call = gsapToCalls.find(c => c.el === container);
    assert.ok(call);
    assert.strictEqual(call.opts.rotateX, 0);
    assert.strictEqual(call.opts.rotateY, 0);
  });

  test("should trigger via DOMContentLoaded if readyState is loading", async () => {
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

    await loadScript();

    assert.strictEqual(addedListener, "DOMContentLoaded");
    assert.ok(addedHandler);

    Object.defineProperty(dom.window.document, "readyState", {
      value: originalReadyState,
      configurable: true,
    });
  });
});
