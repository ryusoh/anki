import test from "node:test";
import assert from "node:assert";
import { JSDOM } from "jsdom";

// ---------------------------------------------------------------------------
// Pins the border-radius logic of TableGlassEffect (js/ui/tableGlassEffect.js):
// - the container's computed borderRadius is parsed with parseInt(..., 10)
//   and applied to the overlay canvas (16px container -> radius 16),
// - excludeHeader forces the canvas radius to 0 (both in style and in draw()),
// - a missing/unparseable computed radius falls back to 8,
// - compound values like "16px 16px 0 0" parse to their first component.
// ---------------------------------------------------------------------------

const dom = new JSDOM("<!DOCTYPE html><html><body></body></html>");

// The module reads bare `document`/`window`/`requestAnimationFrame` globals.
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.requestAnimationFrame = () => 0; // never runs the render loop
globalThis.cancelAnimationFrame = () => {};
dom.window.requestAnimationFrame = globalThis.requestAnimationFrame;
dom.window.cancelAnimationFrame = globalThis.cancelAnimationFrame;

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserverStub;
dom.window.ResizeObserver = ResizeObserverStub;

// jsdom has no canvas 2D implementation; any method the effect calls is a
// no-op, and gradient factories return a stub with addColorStop.
function makeCtxStub() {
  const gradient = { addColorStop() {} };
  return new Proxy(
    {},
    {
      get(target, prop) {
        if (prop in target) {
          return target[prop];
        }
        if (prop === "createLinearGradient" || prop === "createRadialGradient") {
          return () => gradient;
        }
        return () => {};
      },
      set(target, prop, value) {
        target[prop] = value;
        return true;
      },
    },
  );
}
dom.window.HTMLCanvasElement.prototype.getContext = () => makeCtxStub();

// jsdom does not compute border-radius, so control what the effect sees.
function stubComputedStyle(borderRadius) {
  dom.window.getComputedStyle = () => ({
    borderRadius,
    position: "relative",
    overflow: "visible",
    overflowY: "visible",
  });
}

let containerCount = 0;
function makeContainer() {
  const container = document.createElement("div");
  container.id = `glass-container-${containerCount++}`;
  container.innerHTML =
    "<table><thead><tr><th>h</th></tr></thead><tbody><tr><td>a</td></tr></tbody></table>";
  document.body.appendChild(container);
  return container;
}

// Import the real module only after the DOM globals are in place.
const { TableGlassEffect } = await import("#ui/tableGlassEffect.js");

function createEffect(borderRadius, options = {}) {
  stubComputedStyle(borderRadius);
  const container = makeContainer();
  return new TableGlassEffect(`#${container.id}`, options);
}

// Capture the radius draw() hands to every sub-draw call (line ~351:
// `excludeHeader ? 0 : this._borderRadius || 8`).
function drawnRadii(effect) {
  const radii = [];
  effect.drawAmbientGlow = (r) => radii.push(r);
  effect.drawRowHoverEffect = () => {};
  effect.drawElectricTrails = (r) => radii.push(r);
  effect.drawParticles = (r) => radii.push(r);
  effect.drawReflection = (r) => radii.push(r);
  effect.draw();
  return radii;
}

test("computed 16px container radius is applied to the canvas and draw()", () => {
  const effect = createEffect("16px");
  assert.strictEqual(effect._borderRadius, 16);
  assert.strictEqual(effect.canvas.style.borderRadius, "16px");
  assert.deepStrictEqual(drawnRadii(effect), [16, 16, 16, 16]);
  effect.dispose();
});

test("excludeHeader forces the canvas radius to 0", () => {
  const effect = createEffect("16px", { excludeHeader: true });
  // The source assigns "0"; jsdom's CSSOM (29.x+) normalizes unitless zero
  // lengths to "0px" on read-back.
  assert.strictEqual(effect.canvas.style.borderRadius, "0px");
  assert.deepStrictEqual(drawnRadii(effect), [0, 0, 0, 0]);
  effect.dispose();
});

test("missing computed border-radius falls back to 8", () => {
  const effect = createEffect("");
  assert.strictEqual(effect._borderRadius, 8);
  assert.strictEqual(effect.canvas.style.borderRadius, "8px");
  assert.deepStrictEqual(drawnRadii(effect), [8, 8, 8, 8]);
  effect.dispose();
});

test('compound "16px 16px 0 0" parses to its leading component', () => {
  const effect = createEffect("16px 16px 0 0");
  assert.strictEqual(effect._borderRadius, 16);
  assert.strictEqual(effect.canvas.style.borderRadius, "16px");
  assert.deepStrictEqual(drawnRadii(effect), [16, 16, 16, 16]);
  effect.dispose();
});
