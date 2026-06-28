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

  const start = performance.now();
  for (let i = 0; i < 10000; i++) {
    effect.state.continuousPhase = i / 10000;
    effect.drawElectricTrails(10);
  }
  const end = performance.now();
  console.log(`Execution time (original): ${end - start} ms`);
});
