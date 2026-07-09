import test, { describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import { JSDOM } from "jsdom";

describe("Magnetic Nav", () => {
  let dom;
  let gsapToCalls = [];
  let gsapQuickToCalls = [];

  beforeEach(() => {
    dom = new JSDOM(`
      <!DOCTYPE html>
      <html>
      <body>
        <nav class="container">
          <li><a href="#">Link 1</a></li>
          <li><a href="#">Link 2</a></li>
        </nav>
        <div id="currencyToggleContainer">
          <button class="currency-toggle active" data-currency="USD">$</button>
          <button class="currency-toggle" data-currency="CNY">¥</button>
        </div>
        <div id="calendar-navigation-controls">
          <button class="cal-nav-btn" id="cal-prev"><i class="fa fa-chevron-left"></i></button>
          <button class="cal-nav-btn" id="cal-today"><i class="fa fa-circle-o"></i></button>
          <button class="cal-nav-btn" id="cal-next"><i class="fa fa-chevron-right"></i></button>
        </div>
      </body>
      </html>
    `, { url: "http://localhost" });

    globalThis.window = dom.window;
    globalThis.document = dom.window.document;

    gsapToCalls = [];
    gsapQuickToCalls = [];

    dom.window.gsap = {
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

    delete dom.window.ontouchstart;
    Object.defineProperty(globalThis.navigator, "maxTouchPoints", {
      value: 0,
      configurable: true,
      writable: true,
    });
  });

  afterEach(() => {
    delete globalThis.window;
    delete globalThis.document;
  });

  async function loadMagneticNav() {
    await import(`../js/ui/magnetic_nav.js?t=${Date.now()}`);
  }

  test("should attach event listeners and apply magnetic effects on mousemove/mouseleave", async () => {
    await loadMagneticNav();

    const firstLi = document.querySelector("li");
    assert.ok(firstLi);

    // Mock getBoundingClientRect
    firstLi.getBoundingClientRect = () => ({
      left: 10,
      top: 20,
      width: 100,
      height: 100,
    });

    // Mouseenter
    firstLi.dispatchEvent(new dom.window.MouseEvent("mouseenter"));

    // Mousemove
    const mouseMoveEvent = new dom.window.MouseEvent("mousemove", {
      clientX: 60,
      clientY: 70,
    });
    // Set pageX/pageY since jsdom doesn't compute them automatically
    Object.defineProperty(mouseMoveEvent, "pageX", { value: 60 });
    Object.defineProperty(mouseMoveEvent, "pageY", { value: 70 });
    firstLi.dispatchEvent(mouseMoveEvent);

    assert.ok(gsapQuickToCalls.length > 0);
    // Find x/y calls
    const xCall = gsapQuickToCalls.find(c => c.prop === "x" && c.el === firstLi);
    const yCall = gsapQuickToCalls.find(c => c.prop === "y" && c.el === firstLi);
    assert.ok(xCall);
    assert.ok(yCall);

    // Mouseleave
    firstLi.dispatchEvent(new dom.window.MouseEvent("mouseleave"));
    assert.ok(gsapToCalls.length > 0);
    const snapCall = gsapToCalls.find(c => c.el === firstLi);
    assert.ok(snapCall);
    assert.strictEqual(snapCall.opts.x, 0);
    assert.strictEqual(snapCall.opts.y, 0);
  });

  test("should not attach listeners on touch devices", async () => {
    dom.window.ontouchstart = () => {};
    Object.defineProperty(globalThis.navigator, "maxTouchPoints", {
      value: 5,
      configurable: true,
    });

    await loadMagneticNav();

    const firstLi = document.querySelector("li");
    firstLi.getBoundingClientRect = () => ({
      left: 10,
      top: 20,
      width: 100,
      height: 100,
    });

    firstLi.dispatchEvent(new dom.window.MouseEvent("mouseenter"));
    const mouseMoveEvent = new dom.window.MouseEvent("mousemove", { clientX: 60, clientY: 70 });
    firstLi.dispatchEvent(mouseMoveEvent);

    assert.strictEqual(gsapQuickToCalls.length, 0);
  });

  test("should apply magnetic effect to currency toggle buttons", async () => {
    await loadMagneticNav();

    const currencyBtn = document.querySelector("#currencyToggleContainer .currency-toggle");
    assert.ok(currencyBtn);

    currencyBtn.getBoundingClientRect = () => ({
      left: 5,
      top: 5,
      width: 30,
      height: 30,
    });

    currencyBtn.dispatchEvent(new dom.window.MouseEvent("mouseenter"));
    const mouseMoveEvent = new dom.window.MouseEvent("mousemove", { clientX: 20, clientY: 20 });
    Object.defineProperty(mouseMoveEvent, "pageX", { value: 20 });
    Object.defineProperty(mouseMoveEvent, "pageY", { value: 20 });
    currencyBtn.dispatchEvent(mouseMoveEvent);

    assert.ok(gsapQuickToCalls.length > 0);
    const btnXCall = gsapQuickToCalls.find(c => c.el === currencyBtn && c.prop === "x");
    assert.ok(btnXCall);
  });

  test("should apply magnetic effect to calendar navigation buttons in this repo", async () => {
    await loadMagneticNav();

    const calBtn = document.querySelector("#calendar-navigation-controls .cal-nav-btn");
    assert.ok(calBtn);

    calBtn.getBoundingClientRect = () => ({
      left: 5,
      top: 5,
      width: 30,
      height: 30,
    });

    calBtn.dispatchEvent(new dom.window.MouseEvent("mouseenter"));
    const mouseMoveEvent = new dom.window.MouseEvent("mousemove", { clientX: 20, clientY: 20 });
    Object.defineProperty(mouseMoveEvent, "pageX", { value: 20 });
    Object.defineProperty(mouseMoveEvent, "pageY", { value: 20 });
    calBtn.dispatchEvent(mouseMoveEvent);

    assert.ok(gsapQuickToCalls.length > 0);
    const calXCall = gsapQuickToCalls.find(c => c.el === calBtn && c.prop === "x");
    assert.ok(calXCall);
  });
});
