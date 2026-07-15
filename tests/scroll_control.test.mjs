import test, { describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import { JSDOM } from "jsdom";

describe("scroll_control.js", () => {
  let dom;
  let originalPageYOffset;
  let originalScrollTop;
  let scrollToCalled = [];
  let preventDefaultCalls = 0;

  beforeEach(() => {
    dom = new JSDOM("<!DOCTYPE html><html><body></body></html>", { url: "http://localhost" });
    globalThis.window = dom.window;
    globalThis.document = dom.window.document;

    originalPageYOffset = dom.window.pageYOffset;
    originalScrollTop = dom.window.document.documentElement.scrollTop;

    scrollToCalled = [];
    preventDefaultCalls = 0;

    dom.window.scrollTo = (x, y) => {
      scrollToCalled.push({ x, y });
    };

    // Spy on Event.prototype.preventDefault
    const originalPreventDefault = dom.window.Event.prototype.preventDefault;
    dom.window.Event.prototype.preventDefault = function () {
      preventDefaultCalls++;
      originalPreventDefault.apply(this);
    };
  });

  afterEach(() => {
    delete globalThis.window;
    delete globalThis.document;
  });

  async function loadScript() {
    await import(`../js/ui/scroll_control.js?t=${Date.now()}`);
  }

  test("should use document.documentElement.scrollTop when pageYOffset is undefined", async () => {
    await loadScript();

    // Simulate initial scroll position using documentElement.scrollTop
    Object.defineProperty(dom.window, "pageYOffset", { writable: true, value: undefined });
    Object.defineProperty(dom.window.document.documentElement, "scrollTop", { writable: true, value: 100 });
    dom.window.dispatchEvent(new dom.window.Event("scroll"));

    // Simulate scrolling up to the top
    Object.defineProperty(dom.window.document.documentElement, "scrollTop", { writable: true, value: 0 });
    dom.window.dispatchEvent(new dom.window.Event("scroll"));

    assert.strictEqual(scrollToCalled.length, 1);
    assert.deepStrictEqual(scrollToCalled[0], { x: 0, y: 0 });
  });

  test("should call window.scrollTo(0,0) when scrolling up at the very top", async () => {
    await loadScript();

    // Simulate initial scroll position
    Object.defineProperty(dom.window, "pageYOffset", { writable: true, value: 100 });
    Object.defineProperty(dom.window.document.documentElement, "scrollTop", { writable: true, value: 100 });
    dom.window.dispatchEvent(new dom.window.Event("scroll"));

    // Simulate scrolling up to the top
    Object.defineProperty(dom.window, "pageYOffset", { writable: true, value: 0 });
    Object.defineProperty(dom.window.document.documentElement, "scrollTop", { writable: true, value: 0 });
    dom.window.dispatchEvent(new dom.window.Event("scroll"));

    assert.strictEqual(scrollToCalled.length, 1);
    assert.deepStrictEqual(scrollToCalled[0], { x: 0, y: 0 });
  });

  test("should not call window.scrollTo(0,0) when scrolling down", async () => {
    await loadScript();

    // Simulate initial scroll position
    Object.defineProperty(dom.window, "pageYOffset", { writable: true, value: 0 });
    Object.defineProperty(dom.window.document.documentElement, "scrollTop", { writable: true, value: 0 });
    dom.window.dispatchEvent(new dom.window.Event("scroll"));

    // Simulate scrolling down
    Object.defineProperty(dom.window, "pageYOffset", { writable: true, value: 100 });
    Object.defineProperty(dom.window.document.documentElement, "scrollTop", { writable: true, value: 100 });
    dom.window.dispatchEvent(new dom.window.Event("scroll"));

    assert.strictEqual(scrollToCalled.length, 0);
  });

  test("should not call window.scrollTo(0,0) when scrolling up but not at the very top", async () => {
    await loadScript();

    // Simulate initial scroll position
    Object.defineProperty(dom.window, "pageYOffset", { writable: true, value: 100 });
    Object.defineProperty(dom.window.document.documentElement, "scrollTop", { writable: true, value: 100 });
    dom.window.dispatchEvent(new dom.window.Event("scroll"));

    // Simulate scrolling up but not to the top
    Object.defineProperty(dom.window, "pageYOffset", { writable: true, value: 50 });
    Object.defineProperty(dom.window.document.documentElement, "scrollTop", { writable: true, value: 50 });
    dom.window.dispatchEvent(new dom.window.Event("scroll"));

    assert.strictEqual(scrollToCalled.length, 0);
  });

  test("should prevent default touchmove when trying to scroll page up", async () => {
    await loadScript();

    // Simulate touchstart
    const touchStartEvent = new dom.window.TouchEvent("touchstart", {
      touches: [{ clientY: 100 }],
      bubbles: true,
      cancelable: true,
    });
    document.dispatchEvent(touchStartEvent);

    // Simulate touchmove trying to scroll up (finger moves from 100 to 50)
    const touchMoveEvent = new dom.window.TouchEvent("touchmove", {
      touches: [{ clientY: 50 }],
      bubbles: true,
      cancelable: true,
    });
    document.dispatchEvent(touchMoveEvent);

    assert.strictEqual(preventDefaultCalls, 1);
  });

  test("should not prevent default touchmove when trying to scroll page down", async () => {
    await loadScript();

    // Simulate touchstart
    const touchStartEvent = new dom.window.TouchEvent("touchstart", {
      touches: [{ clientY: 50 }],
      bubbles: true,
      cancelable: true,
    });
    document.dispatchEvent(touchStartEvent);

    // Simulate touchmove trying to scroll down (finger moves from 50 to 100)
    const touchMoveEvent = new dom.window.TouchEvent("touchmove", {
      touches: [{ clientY: 100 }],
      bubbles: true,
      cancelable: true,
    });
    document.dispatchEvent(touchMoveEvent);

    assert.strictEqual(preventDefaultCalls, 0);
  });

  test("should not prevent default touchmove when deltaY is zero", async () => {
    await loadScript();

    // Simulate touchstart
    const touchStartEvent = new dom.window.TouchEvent("touchstart", {
      touches: [{ clientY: 50 }],
      bubbles: true,
      cancelable: true,
    });
    document.dispatchEvent(touchStartEvent);

    // Simulate touchmove with no change in Y
    const touchMoveEvent = new dom.window.TouchEvent("touchmove", {
      touches: [{ clientY: 50 }],
      bubbles: true,
      cancelable: true,
    });
    document.dispatchEvent(touchMoveEvent);

    assert.strictEqual(preventDefaultCalls, 0);
  });

  test("should prevent desktop Ctrl/Cmd zoom gestures", async () => {
    await loadScript();

    // Wheel zoom with Ctrl key
    const wheelEvent = new dom.window.WheelEvent("wheel", {
      ctrlKey: true,
      bubbles: true,
      cancelable: true,
    });
    document.dispatchEvent(wheelEvent);
    assert.strictEqual(preventDefaultCalls, 1);

    // Keydown zoom with Ctrl/Cmd
    const keydownEvent = new dom.window.KeyboardEvent("keydown", {
      ctrlKey: true,
      key: "+",
      bubbles: true,
      cancelable: true,
    });
    document.dispatchEvent(keydownEvent);
    assert.strictEqual(preventDefaultCalls, 2);

    // Gesture zoom
    const gestureEvent = new dom.window.Event("gesturestart", {
      bubbles: true,
      cancelable: true,
    });
    document.dispatchEvent(gestureEvent);
    assert.strictEqual(preventDefaultCalls, 3);
  });
});
