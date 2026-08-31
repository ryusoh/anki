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
  // The source assigns "0"; jsdom's CSSOM keeps it as "0" (unitless zero is valid CSS).
  assert.strictEqual(effect.canvas.style.borderRadius, "0");
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

test("throws error when container is not found", () => {
  assert.throws(
    () => new TableGlassEffect("#missing-element-selector"),
    /Container not found/,
  );
});

test("enabled: false disables initialization", () => {
  const container = makeContainer();
  const effect = new TableGlassEffect(`#${container.id}`, { enabled: false });
  assert.strictEqual(effect.canvas, undefined);
});

test("pauseResize and resumeResize toggle resize state", () => {
  const effect = createEffect("8px");
  effect.pauseResize();
  assert.strictEqual(effect.resizePaused, true);
  effect.resumeResize();
  assert.strictEqual(effect.resizePaused, false);
  effect.dispose();
});

test("update, draw, and mouse events execute without errors", () => {
  const effect = createEffect("8px", {
    rowHoverEffect: { enabled: true, color: "rgba(255,255,255,0.1)", borderColor: "rgba(255,255,255,0.2)", spotlightRadius: 200 },
    threeD: { electric: { enabled: true, arcCount: 4 }, reflection: { enabled: true, speed: 0.1 } },
  });

  // Call update steps
  effect.update(1000);
  effect.update(1100);

  // Call mousemove and mouseleave
  effect.containerRect = { left: 0, top: 0, width: 200, height: 200 };
  const mockRow = effect.container.querySelector("tr");
  effect.handleMouseMove({ pageX: 50, pageY: 50, target: mockRow });
  assert.strictEqual(typeof effect.state.pointer.x, "number");

  effect.draw();
  effect.handleMouseLeave();
  assert.strictEqual(effect.state.pointer.x, 0);
  assert.strictEqual(effect.state.hoveredRowIndex, -1);

  effect.draw();
  effect.dispose();
});

test("draw branches for electric disabled and reflection fade multipliers", () => {
  const effect = createEffect("8px", {
    threeD: {
      electric: { enabled: false, particlesEnabled: false },
      reflection: { enabled: true, fadeZone: 0.2 },
    },
  });

  // Test phase < fadeZone
  effect.state.phase = 0.1;
  effect.draw();

  // Test phase > 1 - fadeZone
  effect.state.phase = 0.9;
  effect.draw();

  // Test phase in middle
  effect.state.phase = 0.5;
  effect.draw();

  effect.dispose();
});

test("drawParticles with particles with life property", () => {
  const effect = createEffect("8px", {
    threeD: {
      electric: { enabled: true, particlesEnabled: true },
    },
  });

  effect.state.energyParticles.push({
    life: 0.5,
    progress: 0.5,
    speed: 1,
    size: 2,
    flickerOffset: 0,
  });
  effect.drawParticles(8);
  effect.dispose();
});

test("drawElectricTrails with partial colors palette and dispose cancels animation frame", () => {
  const effect = createEffect("8px", {
    threeD: {
      electric: {
        enabled: true,
        colors: { primary: "rgba(255,255,255,0.8)" }, // only primary, no secondary/tertiary
      },
    },
  });

  effect.drawElectricTrails(8);
  effect.animationFrame = 999;
  effect.dispose();
  assert.strictEqual(effect.canvas.parentNode, null);
});

test("container events and phase wrap in update", () => {
  dom.window.getComputedStyle = () => ({
    borderRadius: "8px",
    position: "static",
    overflow: "auto",
    overflowY: "auto",
  });
  const container = makeContainer();
  Object.defineProperty(container, "scrollHeight", { value: 500, configurable: true });
  Object.defineProperty(container, "clientHeight", { value: 200, configurable: true });

  const effect = new TableGlassEffect(`#${container.id}`, {
    rowHoverEffect: { enabled: true },
  });
  assert.strictEqual(effect._scrollable, true);

  // Dispatch mouseenter, mousemove, mouseleave
  container.dispatchEvent(new dom.window.Event("mouseenter"));
  container.dispatchEvent(new dom.window.MouseEvent("mousemove", { bubbles: true }));
  container.dispatchEvent(new dom.window.Event("mouseleave"));

  // Target not inside a row
  effect.handleMouseMove({ pageX: 10, pageY: 10, target: container });
  assert.strictEqual(effect.state.hoveredRowIndex, -1);

  // Target null
  effect.handleMouseMove({ pageX: 10, pageY: 10, target: null });
  assert.strictEqual(effect.state.hoveredRowIndex, -1);

  // High delta to test wrapping
  effect.state.lastTime = 1000;
  effect.update(100000); // large time jump
  assert.ok(effect.state.phase >= 0 && effect.state.phase < 1);

  effect.dispose();
});
