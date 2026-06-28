// Mock DOM BEFORE importing anything
globalThis.document = {
  createElement: () => ({
    getContext: () => mockCtx,
    style: {},
  }),
  querySelector: () => mockContainer,
  addEventListener: () => {},
};

globalThis.window = {
  scrollX: 0,
  scrollY: 0,
  devicePixelRatio: 1,
  matchMedia: () => ({ matches: false }),
  getComputedStyle: () => ({ overflow: "", overflowY: "" }),
  location: { search: "" },
};

globalThis.ResizeObserver = class {
  observe() {}
  disconnect() {}
};

globalThis.requestAnimationFrame = () => {};
globalThis.cancelAnimationFrame = () => {};

const mockCtx = {
  save: () => {},
  restore: () => {},
  beginPath: () => {},
  moveTo: () => {},
  lineTo: () => {},
  stroke: () => {},
  fill: () => {},
  clip: () => {},
  createLinearGradient: () => ({ addColorStop: () => {} }),
  fillRect: () => {},
  translate: () => {},
  arc: () => {},
  quadraticCurveTo: () => {},
  closePath: () => {},
  clearRect: () => {},
  scale: () => {},
};

const mockContainer = {
  querySelector: () => null,
  addEventListener: () => {},
  getBoundingClientRect: () => ({ left: 0, top: 0, width: 500, height: 300 }),
  appendChild: () => {},
  contains: () => false,
  clientHeight: 300,
  scrollHeight: 300,
};

import("./js/ui/tableGlassEffect.js").then(({ TableGlassEffect }) => {
  const effect = new TableGlassEffect("#mock", {
    threeD: { electric: { enabled: true, colors: { primary: "#fff" } } }
  });

  effect.width = 500;
  effect.height = 300;
  effect._cachedActivePalette = ["#fff", "#f00", "#0f0"];
  effect._cachedActivePaletteLength = 3;

  effect.drawElectricTrailsOptimized = function(radius) {
    const electric = this.options.threeD?.electric || {};
    if (electric.enabled === false) {
      return;
    }

    // Bolt: Cache out objects to avoid creating object allocations in high
    // frequency animation loops, which puts heavy pressure on GC.
    this._p1 = this._p1 || { x: 0, y: 0 };
    this._p2 = this._p2 || { x: 0, y: 0 };

    if (!this._cachedActivePalette) {
      const colors = electric.colors || {};
      const rawPalette = [colors.primary, colors.secondary, colors.tertiary];
      let validPaletteCount = 0;
      for (let i = 0; i < rawPalette.length; i++) {
        if (rawPalette[i]) {
          validPaletteCount++;
        }
      }

      this._cachedActivePalette = rawPalette;
      this._cachedActivePaletteLength = validPaletteCount;

      if (validPaletteCount === 0) {
        this._cachedActivePalette = ["rgba(255, 255, 255, 0.4)"];
        this._cachedActivePaletteLength = 1;
      }
    }

    const activePalette = this._cachedActivePalette;
    const activePaletteLength = this._cachedActivePaletteLength;

    this.ctx.save();
    this.ctx.globalCompositeOperation = "screen"; // Softer than lighter
    this.ctx.lineCap = "round";
    this.ctx.lineWidth = electric.arcThickness || 1.5;

    const trailWidth = electric.width || 0.1;
    const segments = 30; // More segments for smoother gradient

    // Bolt: Precompute loop invariants to eliminate repeated math and division operations
    const invSegments = 1.0 / segments;
    const stepTrailWidth = invSegments * trailWidth;

    let paletteIdx = 0;
    for (let i = 0; i < activePalette.length; i++) {
      const color = activePalette[i];
      if (!color) {
        continue;
      }

      const offset =
        paletteIdx / activePaletteLength +
        this.state.continuousPhase * (electric.streakSpeedMultiplier || 1);
      const headProgress = offset % 1;

      // Bolt: Hoist static canvas state assignments out of the inner render loop
      this.ctx.shadowColor = color;
      this.ctx.shadowBlur = 5;
      this.ctx.strokeStyle = color;

      // Draw trail as segments
      for (let j = 0; j < segments; j++) {
        const segmentProgress = j * invSegments; // 0 to 1
        const p1 = headProgress - segmentProgress * trailWidth;
        const p2 = p1 - stepTrailWidth;

        const point1 = this.getPointAtProgress(p1, radius, this._p1);
        const point2 = this.getPointAtProgress(p2, radius, this._p2);

        // Smooth fade out
        // Use a power curve for more elegant falloff - replaced Math.pow(x, 2) with x * x
        const op = 1 - segmentProgress;
        const opacity = op * op;

        this.ctx.globalAlpha = opacity;

        this.ctx.beginPath();
        this.ctx.moveTo(point1.x, point1.y);
        this.ctx.lineTo(point2.x, point2.y);
        this.ctx.stroke();
      }
      paletteIdx++;
    }

    this.ctx.restore();
  }

  const start = performance.now();
  for (let i = 0; i < 10000; i++) {
    effect.state.continuousPhase = i / 10000;
    effect.drawElectricTrailsOptimized(10);
  }
  const end = performance.now();
  console.log(`Execution time (optimized 2): ${end - start} ms`);
});
