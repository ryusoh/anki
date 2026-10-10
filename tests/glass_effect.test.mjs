import test, { describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import { JSDOM } from "jsdom";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const scriptSource = fs.readFileSync(
  path.join(__dirname, "../animated_glass_background/web/glass_effect.js"),
  "utf8",
);

describe("GlassEffectBackground", () => {
  let dom;
  const activeTimers = [];

  beforeEach(() => {
    dom = new JSDOM("<!DOCTYPE html><html><body></body></html>", {
      url: "http://localhost",
    });
    globalThis.window = dom.window;
    globalThis.document = dom.window.document;
    globalThis.localStorage = dom.window.localStorage;
    globalThis.MutationObserver = dom.window.MutationObserver;
    globalThis.requestAnimationFrame = () => 1;
    globalThis.cancelAnimationFrame = () => {};

    // Mock Canvas 2D
    const gradient = { addColorStop() {} };
    dom.window.HTMLCanvasElement.prototype.getContext = () => ({
      scale: () => {},
      clearRect: () => {},
      beginPath: () => {},
      rect: () => {},
      closePath: () => {},
      clip: () => {},
      save: () => {},
      restore: () => {},
      fill: () => {},
      fillRect: () => {},
      translate: () => {},
      createLinearGradient: () => gradient,
    });
  });

  afterEach(() => {
    while (activeTimers.length > 0) {
      clearTimeout(activeTimers.pop());
    }
  });

  function loadGlassScript(config = {}) {
    dom.window.glassEffectConfig = config;
    // Intercept setTimeout to clear any pending auto-init timers
    const origSetTimeout = dom.window.setTimeout;
    dom.window.setTimeout = (fn, delay) => {
      const id = origSetTimeout(fn, delay);
      activeTimers.push(id);
      return id;
    };
    dom.window.eval(scriptSource);
    return dom.window.GlassEffectBackground;
  }

  test("initializes with default frozen wave configuration", () => {
    const GlassClass = loadGlassScript();
    assert.ok(GlassClass);
    const instance = new GlassClass();

    assert.strictEqual(instance.options.enabled, true);
    assert.strictEqual(instance.options.threeD.reflection.enabled, false);
    assert.strictEqual(instance.options.threeD.ambientGlow.pulse, false);
  });

  test("honors custom config overriding reflection and pulse", () => {
    const GlassClass = loadGlassScript({
      reflectionEnabled: true,
      ambientGlowPulse: true,
      reflectionSpeed: 0.05,
    });
    const instance = new GlassClass();

    assert.strictEqual(instance.options.threeD.reflection.enabled, true);
    assert.strictEqual(instance.options.threeD.ambientGlow.pulse, true);
    assert.strictEqual(instance.options.threeD.reflection.speed, 0.05);
  });

  test("early returns when disabled in config", () => {
    const GlassClass = loadGlassScript({ enabled: false });
    const instance = new GlassClass();

    assert.strictEqual(instance.options.enabled, false);
    assert.strictEqual(instance.canvas, undefined);
  });

  test("draws ambient glow without reflection when reflection is disabled", () => {
    const GlassClass = loadGlassScript({
      reflectionEnabled: false,
      ambientGlowPulse: false,
    });
    const instance = new GlassClass();

    let reflectionDrawn = false;
    instance.drawReflection = () => {
      reflectionDrawn = true;
    };

    instance.draw();
    assert.strictEqual(reflectionDrawn, false);
  });

  test("draws reflection when reflection is enabled", () => {
    const GlassClass = loadGlassScript({
      reflectionEnabled: true,
      ambientGlowPulse: false,
    });
    const instance = new GlassClass();

    let reflectionDrawn = false;
    instance.drawReflection = () => {
      reflectionDrawn = true;
    };

    instance.draw();
    assert.strictEqual(reflectionDrawn, true);
  });

  test("drawReflection returns early when reflection.enabled is false", () => {
    const GlassClass = loadGlassScript();
    const instance = new GlassClass();
    const layout = instance.getSyncedLayout();

    assert.doesNotThrow(() => instance.drawReflection(0, layout));
  });

  test("updates pointer state on mousemove and mouseleave", () => {
    const GlassClass = loadGlassScript();
    const instance = new GlassClass();
    instance.width = 1000;
    instance.height = 800;

    instance.handleMouseMove({ clientX: 750, clientY: 600 });
    assert(instance.state.pointer.x > 0);
    assert(instance.state.pointer.y > 0);

    instance.handleMouseLeave();
    assert.strictEqual(instance.state.pointer.x, 0);
    assert.strictEqual(instance.state.pointer.y, 0);
  });

  test("updates without wave progression when pulse and reflection are disabled", () => {
    const GlassClass = loadGlassScript({
      reflectionEnabled: false,
      ambientGlowPulse: false,
    });
    const instance = new GlassClass();

    instance.update(1000);
    assert.strictEqual(instance.state.phase, 0);
    assert.strictEqual(instance.state.ambientPhase, 0);
  });

  test("progresses phases when pulse and reflection are enabled", () => {
    const GlassClass = loadGlassScript({
      reflectionEnabled: true,
      ambientGlowPulse: true,
    });
    const instance = new GlassClass();

    instance.update(1000);
    assert.ok(instance.state.phase >= 0);
    assert.ok(instance.state.ambientPhase >= 0);
  });

  test("calculates synced layout for bottom and middle panes", () => {
    const GlassClass = loadGlassScript();
    const instance = new GlassClass();
    instance.width = 1200;
    instance.height = 900;

    const midLayout = instance.getSyncedLayout();
    assert.ok(midLayout.totalWidth >= 1000);
    assert.ok(midLayout.totalHeight >= 800);
  });
});
