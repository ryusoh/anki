import test, { describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import { JSDOM } from "jsdom";
import {
  LiquidGlassRefraction,
  supportsSvgBackdropFilter,
  roundedRectSDF,
  maxRefractionShift,
  refractionShift,
  dispersionRatios,
  causticConcentration,
  buildDisplacementMap,
} from "../js/ui/liquidGlassRefraction.js";

function assertCloseTo(actual, expected, precision = 2) {
  const diff = Math.abs(actual - expected);
  const tolerance = Math.pow(10, -precision) / 2;
  assert(
    diff <= tolerance,
    `expected ${actual} to be close to ${expected} (diff: ${diff}, tol: ${tolerance})`,
  );
}

describe("liquidGlassRefraction math", () => {
  describe("roundedRectSDF", () => {
    const halfW = 100;
    const halfH = 50;
    const radius = 10;

    test("is negative inside the rect", () => {
      assert(roundedRectSDF(0, 0, halfW, halfH, radius) < 0);
    });

    test("distance from center equals nearest edge distance", () => {
      assertCloseTo(roundedRectSDF(0, 0, halfW, halfH, radius), -50, 4);
    });

    test("is zero on the straight edge", () => {
      assertCloseTo(roundedRectSDF(0, halfH, halfW, halfH, radius), 0, 4);
      assertCloseTo(roundedRectSDF(halfW, 0, halfW, halfH, radius), 0, 4);
    });

    test("is positive outside", () => {
      assertCloseTo(roundedRectSDF(halfW + 5, 0, halfW, halfH, radius), 5, 4);
      assert(roundedRectSDF(halfW, halfH, halfW, halfH, radius) > 0);
    });

    test("rounds the corner: sharp corner point lies outside", () => {
      const d = roundedRectSDF(halfW, halfH, halfW, halfH, radius);
      assertCloseTo(d, radius * (Math.SQRT2 - 1), 4);
    });
  });

  describe("maxRefractionShift", () => {
    test("matches the critical-angle geometry", () => {
      const ior = 1.5;
      const thickness = 28;
      const expected = thickness * Math.tan(Math.PI / 2 - Math.asin(1 / ior));
      assertCloseTo(maxRefractionShift(ior, thickness), expected, 8);
    });

    test("scales linearly with thickness and grows with ior", () => {
      assertCloseTo(
        maxRefractionShift(1.5, 56),
        2 * maxRefractionShift(1.5, 28),
        8,
      );
      assert(maxRefractionShift(1.7, 28) > maxRefractionShift(1.5, 28));
    });
  });

  describe("refractionShift", () => {
    const bezel = 14;
    const ior = 1.52;
    const thickness = 28;
    const max = maxRefractionShift(ior, thickness);

    test("is zero on the flat interior beyond the bezel", () => {
      assert.strictEqual(refractionShift(bezel, bezel, ior, thickness), 0);
      assert.strictEqual(refractionShift(bezel * 3, bezel, ior, thickness), 0);
    });

    test("clamps to the grazing-incidence maximum at the rim", () => {
      assertCloseTo(refractionShift(0, bezel, ior, thickness), max, 8);
      assertCloseTo(refractionShift(-1, bezel, ior, thickness), max, 8);
    });

    test("decreases monotonically from rim to interior", () => {
      let prev = Infinity;
      for (let d = 0.5; d < bezel; d += 0.5) {
        const s = refractionShift(d, bezel, ior, thickness);
        assert(s > 0);
        assert(s < prev);
        prev = s;
      }
    });

    test("never exceeds the physical maximum", () => {
      for (let d = 0; d <= bezel; d += 0.25) {
        assert(refractionShift(d, bezel, ior, thickness) <= max + 1e-9);
      }
    });
  });

  describe("dispersionRatios", () => {
    test("red bends less, blue bends more", () => {
      const { r, g, b } = dispersionRatios(1.52, 32, 1);
      assert(r < 1);
      assert.strictEqual(g, 1);
      assert(b > 1);
      assertCloseTo(1 - r, b - 1, 8);
    });

    test("zero gain disables dispersion", () => {
      const { r, g, b } = dispersionRatios(1.52, 32, 0);
      assert.strictEqual(r, 1);
      assert.strictEqual(g, 1);
      assert.strictEqual(b, 1);
    });

    test("lower Abbe number means stronger dispersion", () => {
      const flint = dispersionRatios(1.52, 20, 1);
      const crown = dispersionRatios(1.52, 60, 1);
      assert(flint.b - flint.r > crown.b - crown.r);
    });
  });

  describe("causticConcentration", () => {
    const bezel = 14;
    const ior = 1.52;
    const thickness = 28;

    test("concentrates light near the rim", () => {
      assert(causticConcentration(1, bezel, ior, thickness) > 1.5);
    });

    test("is neutral on the flat interior", () => {
      assertCloseTo(
        causticConcentration(bezel * 2, bezel, ior, thickness),
        1,
        5,
      );
    });

    test("decays from rim toward interior", () => {
      const nearRim = causticConcentration(1, bezel, ior, thickness);
      const midBezel = causticConcentration(bezel * 0.6, bezel, ior, thickness);
      assert(nearRim > midBezel);
    });
  });

  describe("buildDisplacementMap", () => {
    const params = {
      width: 200,
      height: 100,
      radius: 12,
      bezelWidth: 14,
      ior: 1.52,
      thickness: 28,
      scale: 0.5,
    };

    const pixelAt = (map, x, y) => {
      const i = (y * map.width + x) * 4;
      return {
        r: map.data[i],
        g: map.data[i + 1],
        b: map.data[i + 2],
        a: map.data[i + 3],
      };
    };

    test("scales map dimensions", () => {
      const map = buildDisplacementMap(params);
      assert.strictEqual(map.width, 100);
      assert.strictEqual(map.height, 50);
      assert.strictEqual(map.data.length, 100 * 50 * 4);
    });

    test("center is neutral (no displacement, no caustic)", () => {
      const map = buildDisplacementMap(params);
      const c = pixelAt(map, 50, 25);
      assert(Math.abs(c.r - 127.5) <= 1);
      assert(Math.abs(c.g - 127.5) <= 1);
      assert.strictEqual(c.b, 0);
    });

    test("encodes the caustic mask in the blue channel at the rim", () => {
      const map = buildDisplacementMap(params);
      assert(pixelAt(map, 0, 25).b > 0);
      assert(pixelAt(map, 50, 0).b > 0);
    });

    test("edges displace inward toward the pane center", () => {
      const map = buildDisplacementMap(params);
      const left = pixelAt(map, 1, 25);
      assert(left.r > 140);
      assert(Math.abs(left.g - 127.5) <= 2);

      const right = pixelAt(map, 98, 25);
      assert(right.r < 115);

      const top = pixelAt(map, 50, 1);
      assert(top.g > 140);

      const bottom = pixelAt(map, 50, 48);
      assert(bottom.g < 115);
    });

    test("map is fully opaque", () => {
      const map = buildDisplacementMap(params);
      for (let i = 3; i < map.data.length; i += 4) {
        assert.strictEqual(map.data[i], 255);
      }
    });

    test("reports the encoding normalisation", () => {
      const map = buildDisplacementMap(params);
      assertCloseTo(
        map.maxShift,
        maxRefractionShift(params.ior, params.thickness),
        8,
      );
    });

    describe("interior magnification (bulge)", () => {
      const magParams = { ...params, scale: 1, magnification: 0.15 };
      const shiftAt = (map, x, y) => {
        const i = (y * map.width + x) * 4;
        return {
          dx: ((map.data[i] - 127.5) / 127.5) * map.maxShift,
          dy: ((map.data[i + 1] - 127.5) / 127.5) * map.maxShift,
        };
      };

      test("leaves the centre neutral", () => {
        const s = shiftAt(buildDisplacementMap(magParams), 100, 50);
        assert(Math.abs(s.dx) < 0.5);
        assert(Math.abs(s.dy) < 0.5);
      });

      test("pulls an interior pixel inward where rim refraction is zero", () => {
        const plain = shiftAt(
          buildDisplacementMap({ ...params, scale: 1 }),
          20,
          50,
        );
        const bulged = shiftAt(buildDisplacementMap(magParams), 20, 50);
        assert(Math.abs(plain.dx) < 0.5);
        assert(bulged.dx > 4);
      });

      test("tapers to ~zero added shift at the rim", () => {
        const plain = shiftAt(
          buildDisplacementMap({ ...params, scale: 1 }),
          0,
          50,
        );
        const bulged = shiftAt(buildDisplacementMap(magParams), 0, 50);
        assert(Math.abs(bulged.dx - plain.dx) < 2.5);
      });

      test("widens maxShift to fit added bulge", () => {
        const plain = buildDisplacementMap({ ...params });
        const bulged = buildDisplacementMap({ ...params, magnification: 0.15 });
        assert(bulged.maxShift > plain.maxShift);
      });

      test("does not apply to annulus shape", () => {
        const ring = {
          width: 200,
          height: 200,
          radius: 0,
          bezelWidth: 10,
          ior: 1.52,
          thickness: 18,
          scale: 1,
          shape: "annulus",
          innerRadiusRatio: 0.5,
        };
        const plain = buildDisplacementMap(ring);
        const withMag = buildDisplacementMap({ ...ring, magnification: 0.3 });
        assertCloseTo(withMag.maxShift, plain.maxShift, 8);
      });
    });

    describe("annulus shape (glass donut)", () => {
      const ringParams = {
        width: 200,
        height: 200,
        radius: 0,
        bezelWidth: 10,
        ior: 1.52,
        thickness: 18,
        scale: 0.5,
        shape: "annulus",
        innerRadiusRatio: 0.5,
      };

      test("hole center and mid-ring stay neutral", () => {
        const map = buildDisplacementMap(ringParams);
        const hole = pixelAt(map, 50, 50);
        assert(Math.abs(hole.r - 127.5) <= 1);
        assert(Math.abs(hole.g - 127.5) <= 1);
        assert.strictEqual(hole.b, 0);

        const band = pixelAt(map, 87, 50);
        assert(Math.abs(band.r - 127.5) <= 1);
        assert.strictEqual(band.b, 0);
      });

      test("outer rim displaces inward, inner rim outward, both with caustics", () => {
        const map = buildDisplacementMap(ringParams);
        const outer = pixelAt(map, 99, 50);
        assert(outer.r < 115);
        assert(outer.b > 0);

        const inner = pixelAt(map, 75, 50);
        assert(inner.r > 140);
        assert(inner.b > 0);
      });
    });
  });
});

describe("supportsSvgBackdropFilter", () => {
  test("is disabled outside Chromium (jsdom has no Chrome UA)", () => {
    assert.strictEqual(supportsSvgBackdropFilter(), false);
  });

  test("returns true for Chromium without reduced-transparency", () => {
    const localDom = new JSDOM("<!DOCTYPE html><html><body></body></html>");
    const origWin = globalThis.window;
    const origDoc = globalThis.document;
    const origNavDesc = Object.getOwnPropertyDescriptor(
      globalThis,
      "navigator",
    );

    globalThis.window = localDom.window;
    globalThis.document = localDom.window.document;
    Object.defineProperty(globalThis, "navigator", {
      value: {
        userAgent:
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
      },
      configurable: true,
    });

    globalThis.window.matchMedia = () => ({ matches: false });
    assert.strictEqual(supportsSvgBackdropFilter(), true);

    globalThis.window.matchMedia = () => ({ matches: true });
    assert.strictEqual(supportsSvgBackdropFilter(), false);

    if (origNavDesc) {
      Object.defineProperty(globalThis, "navigator", origNavDesc);
    }
    globalThis.window = origWin;
    globalThis.document = origDoc;
  });
});

describe("LiquidGlassRefraction lifecycle", () => {
  let dom;
  let element;
  let originalGetContext;
  let originalToBlob;
  let originalCreateObjectURL;
  let originalRevokeObjectURL;
  let originalRaf;
  let originalResizeObserver;

  beforeEach(() => {
    dom = new JSDOM("<!DOCTYPE html><html><body></body></html>");
    globalThis.window = dom.window;
    globalThis.document = dom.window.document;
    globalThis.Blob = dom.window.Blob;

    element = dom.window.document.createElement("div");
    Object.defineProperties(element, {
      clientWidth: { value: 200, configurable: true },
      clientHeight: { value: 100, configurable: true },
      offsetWidth: { value: 200, configurable: true },
      offsetHeight: { value: 100, configurable: true },
    });
    dom.window.document.body.appendChild(element);

    originalGetContext = dom.window.HTMLCanvasElement.prototype.getContext;
    originalToBlob = dom.window.HTMLCanvasElement.prototype.toBlob;
    dom.window.HTMLCanvasElement.prototype.getContext = () => ({
      createImageData: (w, h) => ({ data: new Uint8ClampedArray(w * h * 4) }),
      putImageData: () => {},
    });
    dom.window.HTMLCanvasElement.prototype.toBlob = function (cb) {
      cb(new dom.window.Blob(["x"], { type: "image/png" }));
    };

    originalCreateObjectURL = globalThis.URL.createObjectURL;
    originalRevokeObjectURL = globalThis.URL.revokeObjectURL;
    globalThis.URL.createObjectURL = () => "blob:mock";
    globalThis.URL.revokeObjectURL = () => {};

    originalRaf = globalThis.requestAnimationFrame;
    let inRaf = false;
    globalThis.requestAnimationFrame = (cb) => {
      if (!inRaf) {
        inRaf = true;
        try {
          cb();
        } finally {
          inRaf = false;
        }
      }
      return 1;
    };
    globalThis.cancelAnimationFrame = () => {};

    originalResizeObserver = globalThis.ResizeObserver;
    globalThis.ResizeObserver = class {
      constructor(cb) {
        this._callback = cb;
      }
      observe() {}
      unobserve() {}
      disconnect() {}
    };
  });

  afterEach(() => {
    if (element && element.parentNode) {
      element.parentNode.removeChild(element);
    }
    dom.window.HTMLCanvasElement.prototype.getContext = originalGetContext;
    dom.window.HTMLCanvasElement.prototype.toBlob = originalToBlob;
    globalThis.URL.createObjectURL = originalCreateObjectURL;
    globalThis.URL.revokeObjectURL = originalRevokeObjectURL;
    globalThis.requestAnimationFrame = originalRaf;
    globalThis.ResizeObserver = originalResizeObserver;
    dom.window.document.querySelectorAll("svg").forEach((svg) => svg.remove());
  });

  test("stays inert when browser is unsupported", () => {
    const effect = new LiquidGlassRefraction(element);
    assert.strictEqual(effect.enabled, false);
    assert.strictEqual(dom.window.document.querySelector("svg"), null);
    assert.strictEqual(element.style.backdropFilter || "", "");
    assert.doesNotThrow(() => effect.dispose());
  });

  test("builds SVG filter chain and applies backdrop-filter when forced", () => {
    const effect = new LiquidGlassRefraction(element, {
      force: true,
      frost: "blur(5px)",
    });

    assert.strictEqual(effect.enabled, true);
    const filter = dom.window.document.querySelector("svg defs filter");
    assert(filter !== null);
    assert.strictEqual(filter.querySelectorAll("feDisplacementMap").length, 3);
    assert.strictEqual(filter.querySelectorAll("feColorMatrix").length, 4);
    assert.strictEqual(filter.querySelectorAll("feComposite").length, 3);

    assert(element.style.backdropFilter.includes(`url(#${effect.filterId})`));
    assert(element.style.backdropFilter.includes("blur(5px)"));

    const scales = Array.from(filter.querySelectorAll("feDisplacementMap")).map(
      (node) => parseFloat(node.getAttribute("scale")),
    );
    assert(scales[0] < scales[1]);
    assert(scales[1] < scales[2]);

    effect.dispose();
  });

  test("magnification stays single displacement stage reading SourceGraphic", () => {
    const effect = new LiquidGlassRefraction(element, {
      force: true,
      frost: "",
      magnification: 0.1,
    });

    const filter = dom.window.document.querySelector("svg defs filter");
    assert.strictEqual(filter.querySelectorAll("feImage").length, 1);
    const disps = Array.from(filter.querySelectorAll("feDisplacementMap"));
    assert.strictEqual(disps.length, 3);
    disps.forEach((node) =>
      assert.strictEqual(node.getAttribute("in"), "SourceGraphic"),
    );

    effect.dispose();
  });

  test("builds lens at border-box, not clientWidth", () => {
    Object.defineProperties(element, {
      clientWidth: { value: 200, configurable: true },
      clientHeight: { value: 100, configurable: true },
      offsetWidth: { value: 215, configurable: true },
      offsetHeight: { value: 100, configurable: true },
    });

    const effect = new LiquidGlassRefraction(element, {
      force: true,
      frost: "",
      radius: 16,
    });
    assert(effect._lastGeometry.includes("215x100"));
    assert(!effect._lastGeometry.includes("200x100"));

    effect.dispose();
  });

  test("explicit radius option overrides computed border-radius", () => {
    const effect = new LiquidGlassRefraction(element, {
      force: true,
      frost: "",
      radius: 24,
    });
    assert(effect._lastGeometry.includes("200x100r24"));
    effect.dispose();
  });

  test("rampMs thickens lens in from zero strength", () => {
    const queue = [];
    globalThis.requestAnimationFrame = (cb) => {
      queue.push(cb);
      return queue.length;
    };
    const pump = () => {
      queue.splice(0).forEach((cb) => cb());
    };
    let now = 1000;
    const origNow = globalThis.performance.now;
    globalThis.performance.now = () => now;

    const effect = new LiquidGlassRefraction(element, {
      force: true,
      frost: "",
      rampMs: 400,
    });
    pump();

    const scales = () =>
      Array.from(
        dom.window.document.querySelectorAll(
          "svg defs filter feDisplacementMap",
        ),
      ).map((n) => parseFloat(n.getAttribute("scale")));
    const caustic = dom.window.document.querySelector(
      'svg defs filter feComposite[k3="0"]',
    );

    assert(element.style.backdropFilter.includes("url(#"));
    assert(scales().every((s) => s === 0));
    assert.strictEqual(parseFloat(caustic.getAttribute("k1")), 0);

    now = 1200;
    pump();
    const mid = scales();
    assert(mid[1] > 0);
    assert(mid[1] < effect._baseScale);

    now = 1500;
    pump();
    assertCloseTo(scales()[1], effect._baseScale, 5);
    assertCloseTo(parseFloat(caustic.getAttribute("k1")), 0.7, 5);
    assert.strictEqual(effect._rampActive, false);

    globalThis.performance.now = origNow;
    effect.dispose();
  });

  test("omits caustic nodes when causticGain is zero", () => {
    const effect = new LiquidGlassRefraction(element, {
      force: true,
      frost: "",
      causticGain: 0,
    });
    const filter = dom.window.document.querySelector("svg defs filter");
    assert.strictEqual(filter.querySelectorAll("feColorMatrix").length, 3);
    assert.strictEqual(filter.querySelectorAll("feComposite").length, 2);
    effect.dispose();
  });

  test("skips rebuild when geometry is unchanged", () => {
    const effect = new LiquidGlassRefraction(element, {
      force: true,
      frost: "",
    });
    const href = effect.feImage.getAttribute("href");
    assert.strictEqual(href, "blob:mock");

    globalThis.URL.createObjectURL = () => "blob:new";
    effect.update();
    assert.strictEqual(effect.feImage.getAttribute("href"), href);

    effect.dispose();
  });

  test("dispose removes filter, clears style, and releases shared svg", () => {
    const effect = new LiquidGlassRefraction(element, {
      force: true,
      frost: "",
    });
    assert(dom.window.document.querySelector("svg") !== null);
    assert(element.style.backdropFilter !== "");

    effect.dispose();

    assert.strictEqual(element.style.backdropFilter, "");
    assert.strictEqual(
      dom.window.document.querySelector("svg defs filter"),
      null,
    );
    assert.strictEqual(dom.window.document.querySelector("svg"), null);
  });

  test("multiple instances share one svg and release with last dispose", () => {
    const second = dom.window.document.createElement("div");
    Object.defineProperties(second, {
      clientWidth: { value: 120, configurable: true },
      clientHeight: { value: 80, configurable: true },
    });
    dom.window.document.body.appendChild(second);

    const a = new LiquidGlassRefraction(element, { force: true, frost: "" });
    const b = new LiquidGlassRefraction(second, { force: true, frost: "" });

    assert.strictEqual(dom.window.document.querySelectorAll("svg").length, 1);
    assert.strictEqual(
      dom.window.document.querySelectorAll("svg defs filter").length,
      2,
    );
    assert.notStrictEqual(a.filterId, b.filterId);

    a.dispose();
    assert(dom.window.document.querySelector("svg") !== null);
    b.dispose();
    assert.strictEqual(dom.window.document.querySelector("svg"), null);

    second.remove();
  });

  test("encodes map via toBlob and assigns blob URL", () => {
    const effect = new LiquidGlassRefraction(element, {
      force: true,
      frost: "",
    });
    assert.strictEqual(effect.feImage.getAttribute("href"), "blob:mock");
    effect.dispose();
  });

  test("revokes blob URL on dispose", () => {
    let revoked = null;
    globalThis.URL.revokeObjectURL = (u) => {
      revoked = u;
    };
    const effect = new LiquidGlassRefraction(element, {
      force: true,
      frost: "",
    });
    effect.dispose();
    assert.strictEqual(revoked, "blob:mock");
  });

  test("debounces ResizeObserver-driven updates", async () => {
    let scheduleUpdateCalls = 0;
    const originalScheduleUpdate =
      LiquidGlassRefraction.prototype._scheduleUpdate;
    LiquidGlassRefraction.prototype._scheduleUpdate = function () {
      scheduleUpdateCalls += 1;
      return originalScheduleUpdate.call(this);
    };

    const effect = new LiquidGlassRefraction(element, {
      force: true,
      frost: "",
    });
    scheduleUpdateCalls = 0;

    effect.resizeObserver._callback();
    effect.resizeObserver._callback();
    effect.resizeObserver._callback();

    assert.strictEqual(scheduleUpdateCalls, 0);

    await new Promise((resolve) => setTimeout(resolve, 150));
    assert.strictEqual(scheduleUpdateCalls, 1);

    effect.dispose();
    LiquidGlassRefraction.prototype._scheduleUpdate = originalScheduleUpdate;
  });

  test("sets displacement scale to zero when displacementGain is 0 while keeping caustic", () => {
    const effect = new LiquidGlassRefraction(element, {
      force: true,
      frost: "",
      displacementGain: 0,
      causticGain: 0.8,
    });
    assert.strictEqual(effect.displacementNodes.r.getAttribute("scale"), "0");
    assert.strictEqual(effect.displacementNodes.g.getAttribute("scale"), "0");
    assert.strictEqual(effect.displacementNodes.b.getAttribute("scale"), "0");
    assert.strictEqual(effect._causticNode.getAttribute("k1"), "0.8");
    effect.dispose();
  });

  test("spectralCaustic creates chromatic dispersion nodes and sets scale/k3", () => {
    const effect = new LiquidGlassRefraction(element, {
      force: true,
      frost: "",
      displacementGain: 0,
      causticGain: 0.8,
      spectralCaustic: true,
      spectralSpread: 12,
    });
    assert(effect.causticDisplacementNodes !== undefined);
    assert.strictEqual(
      effect.causticDisplacementNodes.r.getAttribute("scale"),
      "12",
    );
    assert.strictEqual(
      effect.causticDisplacementNodes.b.getAttribute("scale"),
      "-12",
    );
    assert.strictEqual(effect._causticNode.getAttribute("k1"), "0.8");
    assertCloseTo(parseFloat(effect._causticNode.getAttribute("k3")), 0.4, 5);
    effect.dispose();
  });

  test("buildDisplacementMap supports smooth causticProfile", () => {
    const mapSlope = buildDisplacementMap({
      width: 200,
      height: 100,
      radius: 8,
      bezelWidth: 18,
      ior: 1.52,
      thickness: 26,
      causticProfile: "slope",
    });
    const mapSmooth = buildDisplacementMap({
      width: 200,
      height: 100,
      radius: 8,
      bezelWidth: 18,
      ior: 1.52,
      thickness: 26,
      causticProfile: "smooth",
    });

    const pixelAt = (map, x, y) => {
      const i = (y * map.width + x) * 4;
      return {
        r: map.data[i],
        g: map.data[i + 1],
        b: map.data[i + 2],
        a: map.data[i + 3],
      };
    };

    const midSlope = pixelAt(mapSlope, 3, 25);
    const midSmooth = pixelAt(mapSmooth, 3, 25);
    assert.strictEqual(midSlope.b, 0);
    assert(midSmooth.b > 100);
  });

  test("does not initialize effect when options.enabled is false", () => {
    const effect = new LiquidGlassRefraction(element, {
      force: true,
      enabled: false,
    });
    assert.strictEqual(effect.enabled, false);
    assert.strictEqual(effect.filter, undefined);
    effect.dispose();
  });

  test("disables when canvas 2d context cannot be created", () => {
    dom.window.HTMLCanvasElement.prototype.getContext = () => null;
    const effect = new LiquidGlassRefraction(element, { force: true });
    assert.strictEqual(effect.enabled, false);
  });

  test("inherits stylesheet frost when frost option is null", () => {
    dom.window.getComputedStyle = () => ({
      backdropFilter: "blur(18px) saturate(1.5)",
    });
    const effect = new LiquidGlassRefraction(element, {
      force: true,
      frost: null,
    });
    assert(element.style.backdropFilter.includes("blur(18px) saturate(1.5)"));
    effect.dispose();
  });

  test("parses percentage border-radius", () => {
    dom.window.getComputedStyle = () => ({
      borderTopLeftRadius: "50%",
    });
    const effect = new LiquidGlassRefraction(element, {
      force: true,
      radius: null,
    });
    assert(effect._lastGeometry.includes("r50"));
    effect.dispose();
  });

  test("falls back to 0 on unparseable border-radius", () => {
    dom.window.getComputedStyle = () => ({
      borderTopLeftRadius: "none",
    });
    const effect = new LiquidGlassRefraction(element, {
      force: true,
      radius: null,
    });
    assert(effect._lastGeometry.includes("r0"));
    effect.dispose();
  });

  test("update returns early when dimensions are < 2 or element disconnected", () => {
    const effect = new LiquidGlassRefraction(element, { force: true });
    const lastGeo = effect._lastGeometry;
    Object.defineProperties(element, {
      offsetWidth: { value: 1, configurable: true },
      offsetHeight: { value: 1, configurable: true },
    });
    effect.update();
    assert.strictEqual(effect._lastGeometry, lastGeo);

    Object.defineProperties(element, {
      offsetWidth: { value: 200, configurable: true },
      offsetHeight: { value: 100, configurable: true },
      isConnected: { value: false, configurable: true },
    });
    effect.update();
    assert.strictEqual(effect._lastGeometry, lastGeo);
    effect.dispose();
  });

  test("ignores stale toBlob callbacks or empty blob", () => {
    let capturedCb = null;
    dom.window.HTMLCanvasElement.prototype.toBlob = (cb) => {
      capturedCb = cb;
    };
    const effect = new LiquidGlassRefraction(element, { force: true });
    capturedCb(null);
    effect._mapGeneration += 1;
    capturedCb(new dom.window.Blob(["x"], { type: "image/png" }));
    effect.dispose();
  });

  test("dispose clears active debounce timer and terminates active ramp", () => {
    const effect = new LiquidGlassRefraction(element, {
      force: true,
      rampMs: 500,
    });
    effect._resizeDebounceTimer = setTimeout(() => {}, 1000);
    assert.strictEqual(effect._rampActive, true);
    effect.dispose();
    assert.strictEqual(effect._resizeDebounceTimer, null);
    assert.strictEqual(effect.enabled, false);
  });

  test("_startRamp returns early if already active", () => {
    const effect = new LiquidGlassRefraction(element, {
      force: true,
      rampMs: 500,
    });
    effect._startRamp();
    assert.strictEqual(effect._rampActive, true);
    effect._startRamp();
    effect.dispose();
  });

  test("supports annulus shape in LiquidGlassRefraction", () => {
    const effect = new LiquidGlassRefraction(element, {
      force: true,
      shape: "annulus",
      innerRadiusRatio: 0.5,
    });
    assert(effect._lastGeometry.includes("sannulus"));
    effect.dispose();
  });
});
