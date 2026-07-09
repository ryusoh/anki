import test, { describe, beforeEach, afterEach, before, after } from "node:test";
import assert from "node:assert";
import fs from "node:fs";
import path from "node:path";
import { JSDOM } from "jsdom";

const mockThreeJsSource = `
export class WebGLRenderer {
  constructor() {
    this.domElement = document.createElement('canvas');
  }
  setSize() {}
  setPixelRatio() {}
  setClearColor() {}
  render() {}
}
export class Scene {
  constructor() {
    this.background = null;
  }
  add() {}
}
export class PerspectiveCamera {
  constructor() {
    this.position = { x: 0, y: 0, z: 0 };
  }
  lookAt() {}
  updateProjectionMatrix() {}
}
export class Color {
  constructor() {}
  setHex() {}
}
export class Vector2 {
  constructor(x, y) {
    this.x = x || 0;
    this.y = y || 0;
  }
  set(x, y) {
    this.x = x;
    this.y = y;
  }
  copy(v) {
    this.x = v.x;
    this.y = v.y;
  }
  lerp(v, alpha) {
    this.x += (v.x - this.x) * alpha;
    this.y += (v.y - this.y) * alpha;
  }
}
export class Vector3 {
  constructor(x, y, z) {
    this.x = x || 0;
    this.y = y || 0;
    this.z = z || 0;
  }
}
export class BufferGeometry {
  constructor() {}
  setAttribute() {}
}
export class BufferAttribute {
  constructor() {}
}
export class PlaneGeometry {
  constructor() {}
}
export class RingGeometry {
  constructor() {}
}
export class ShaderMaterial {
  constructor(opts) {
    this.uniforms = opts.uniforms;
  }
}
export class Mesh {
  constructor() {
    this.rotation = { x: 0, y: 0, z: 0 };
    this.position = { x: 0, y: 0, z: 0 };
  }
}
export class Points {
  constructor() {
    this.rotation = { x: 0, y: 0, z: 0 };
    this.position = { x: 0, y: 0, z: 0 };
  }
}
export class Group {
  constructor() {
    this.rotation = { x: 0, y: 0, z: 0 };
    this.position = { x: 0, y: 0, z: 0 };
  }
  add() {}
}
export const DoubleSide = 2;
export const AdditiveBlending = 2;
`;

describe("quantum_shader normal path", () => {
  let dom;
  let originalConsoleError;
  let originalConsoleWarn;
  const mockThreeDir = path.join(process.cwd(), "node_modules", "three");

  before(() => {
    if (!fs.existsSync(mockThreeDir)) {
      fs.mkdirSync(mockThreeDir, { recursive: true });
    }
    fs.writeFileSync(path.join(mockThreeDir, "package.json"), JSON.stringify({ name: "three", type: "module", main: "./index.js" }));
    fs.writeFileSync(path.join(mockThreeDir, "index.js"), mockThreeJsSource);
  });

  after(() => {
    try {
      fs.rmSync(mockThreeDir, { recursive: true, force: true });
    } catch (e) {}
  });

  beforeEach(() => {
    dom = new JSDOM("<!DOCTYPE html><html><body><div id='appContent'></div></body></html>", { url: "http://localhost" });
    globalThis.window = dom.window;
    globalThis.document = dom.window.document;
    originalConsoleError = globalThis.console.error;
    originalConsoleWarn = globalThis.console.warn;
    globalThis.console.error = () => {};
    globalThis.console.warn = () => {};

    globalThis.requestAnimationFrame = (cb) => setTimeout(() => cb(100), 0);
    globalThis.cancelAnimationFrame = (id) => clearTimeout(id);
    dom.window.requestAnimationFrame = globalThis.requestAnimationFrame;
    dom.window.cancelAnimationFrame = globalThis.cancelAnimationFrame;

    const originalCreateElement = dom.window.document.createElement.bind(dom.window.document);
    dom.window.document.createElement = (tagName) => {
      const el = originalCreateElement(tagName);
      if (tagName === "canvas") {
        el.width = 100;
        el.height = 100;
        el.getContext = () => ({
          createImageData: () => ({
            data: new Uint8ClampedArray(40000),
          }),
          putImageData: () => {},
          fillRect: () => {},
          clearRect: () => {},
          fill: () => {},
          beginPath: () => {},
        });
      }
      return el;
    };

    dom.window.ResizeObserver = class {
      observe() {}
      unobserve() {}
      disconnect() {}
    };
    globalThis.ResizeObserver = dom.window.ResizeObserver;
  });

  afterEach(() => {
    globalThis.console.error = originalConsoleError;
    globalThis.console.warn = originalConsoleWarn;
    delete globalThis.window;
    delete globalThis.document;
    delete globalThis.ResizeObserver;
  });

  test("initializes normal rendering path and handles pointer/keyboard events", async () => {
    Object.defineProperty(document, "readyState", {
      value: "complete",
      configurable: true,
    });

    await import(`../js/ambient/quantum_shader.js?t=${Date.now()}`);

    // Wait for the dynamic import and DOMContentLoaded callback resolving
    await new Promise((resolve) => setTimeout(resolve, 50));

    const container = document.querySelector(".quantum-widget");
    assert.ok(container);

    // Trigger pointer events
    let event = new dom.window.MouseEvent("pointermove", { clientX: 50, clientY: 50 });
    container.dispatchEvent(event);

    event = new dom.window.MouseEvent("pointerdown", { clientX: 50, clientY: 50 });
    event.pointerId = 1;
    container.setPointerCapture = () => {};
    container.dispatchEvent(event);

    event = new dom.window.MouseEvent("pointerdown", { clientX: 50, clientY: 50 });
    event.pointerId = 2;
    container.setPointerCapture = () => {
      throw new Error("Capture error");
    };
    container.dispatchEvent(event);

    event = new dom.window.MouseEvent("pointermove", { clientX: 100, clientY: 100 });
    event.pointerId = 2;
    container.dispatchEvent(event);

    event = new dom.window.MouseEvent("pointermove", { clientX: 100, clientY: 100 });
    event.pointerId = 1;
    container.dispatchEvent(event);

    event = new dom.window.MouseEvent("pointerup");
    event.pointerId = 2;
    container.releasePointerCapture = () => {};
    container.hasPointerCapture = () => true;
    container.dispatchEvent(event);

    event = new dom.window.MouseEvent("pointerup");
    event.pointerId = 1;
    container.dispatchEvent(event);

    // release error path
    event = new dom.window.MouseEvent("pointerup");
    event.pointerId = 2;
    const downEvent = new dom.window.MouseEvent("pointerdown", { clientX: 50, clientY: 50 });
    downEvent.pointerId = 2;
    container.setPointerCapture = () => {};
    container.dispatchEvent(downEvent);
    container.releasePointerCapture = () => {
      throw new Error("Release error");
    };
    container.dispatchEvent(event);

    event = new dom.window.MouseEvent("pointercancel");
    event.pointerId = 2;
    container.dispatchEvent(event);

    event = new dom.window.MouseEvent("pointerleave");
    container.dispatchEvent(event);

    // pointerleave while active
    const dEvent = new dom.window.MouseEvent("pointerdown", { clientX: 50, clientY: 50 });
    dEvent.pointerId = 2;
    container.dispatchEvent(dEvent);
    container.dispatchEvent(event);

    container.dispatchEvent(new dom.window.Event("contextmenu"));

    dom.window.dispatchEvent(new dom.window.Event("blur"));
    dom.window.dispatchEvent(new dom.window.Event("resize"));

    document.dispatchEvent(new dom.window.KeyboardEvent("keydown", { key: "ArrowUp" }));
    document.dispatchEvent(new dom.window.KeyboardEvent("keydown", { key: "ArrowDown", shiftKey: true }));
    document.dispatchEvent(new dom.window.KeyboardEvent("keydown", { key: "ArrowLeft" }));
    document.dispatchEvent(new dom.window.KeyboardEvent("keydown", { key: "ArrowRight", shiftKey: true }));
    document.dispatchEvent(new dom.window.KeyboardEvent("keydown", { key: "Space" }));

    // isContentEditable target
    const mockEvent = new dom.window.KeyboardEvent("keydown", { key: "ArrowUp" });
    const mockTarget = dom.window.document.createElement("div");
    Object.defineProperty(mockTarget, "isContentEditable", { value: true, enumerable: true });
    Object.defineProperty(mockEvent, "target", { value: mockTarget, enumerable: true });
    document.dispatchEvent(mockEvent);

    // textarea / input target
    const input = dom.window.document.createElement("input");
    dom.window.document.body.appendChild(input);
    input.dispatchEvent(new dom.window.KeyboardEvent("keydown", { key: "ArrowUp" }));
  });
});
