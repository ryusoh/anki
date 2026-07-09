import test, { describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import { JSDOM } from "jsdom";

describe("reduced_motion.js", () => {
  let dom;
  let originalConsoleWarn;

  beforeEach(() => {
    dom = new JSDOM("<!DOCTYPE html><html><body></body></html>", { url: "http://localhost" });
    globalThis.window = dom.window;
    globalThis.document = dom.window.document;
    originalConsoleWarn = globalThis.console.warn;
    globalThis.console.warn = () => {};
  });

  afterEach(() => {
    delete globalThis.window;
    delete globalThis.document;
    globalThis.console.warn = originalConsoleWarn;
  });

  async function loadScript() {
    await import(`../js/ui/reduced_motion.js?t=${Date.now()}`);
  }

  test("pauses background video when prefers-reduced-motion matches", async () => {
    document.body.innerHTML = `
      <div class="video-background">
        <video autoplay></video>
      </div>
    `;

    const video = document.querySelector(".video-background video");
    let paused = false;
    video.pause = () => {
      paused = true;
    };

    dom.window.matchMedia = (query) => {
      assert.strictEqual(query, "(prefers-reduced-motion: reduce)");
      return { matches: true };
    };

    await loadScript();

    assert.strictEqual(paused, true);
    assert.strictEqual(video.hasAttribute("autoplay"), false);
  });

  test("does nothing when prefers-reduced-motion does not match", async () => {
    document.body.innerHTML = `
      <div class="video-background">
        <video autoplay></video>
      </div>
    `;

    const video = document.querySelector(".video-background video");
    let paused = false;
    video.pause = () => {
      paused = true;
    };

    dom.window.matchMedia = (query) => {
      return { matches: false };
    };

    await loadScript();

    assert.strictEqual(paused, false);
    assert.strictEqual(video.hasAttribute("autoplay"), true);
  });

  test("gracefully handles missing video element even when motion reduced", async () => {
    document.body.innerHTML = '<div class="video-background"></div>';
    dom.window.matchMedia = () => ({ matches: true });

    await assert.doesNotReject(loadScript);
  });

  test("handles environments without matchMedia gracefully", async () => {
    document.body.innerHTML = `
      <div class="video-background">
        <video autoplay></video>
      </div>
    `;

    const video = document.querySelector(".video-background video");
    let paused = false;
    video.pause = () => {
      paused = true;
    };

    delete dom.window.matchMedia;

    await assert.doesNotReject(loadScript);
    assert.strictEqual(paused, false);
    assert.strictEqual(video.hasAttribute("autoplay"), true);
  });

  test("ignores errors thrown during execution", async () => {
    document.body.innerHTML = `
      <div class="video-background">
        <video autoplay></video>
      </div>
    `;

    const video = document.querySelector(".video-background video");
    let paused = false;
    video.pause = () => {
      paused = true;
    };

    dom.window.matchMedia = () => {
      throw new Error("matchMedia error");
    };

    await assert.doesNotReject(loadScript);
    assert.strictEqual(paused, false);
    assert.strictEqual(video.hasAttribute("autoplay"), true);
  });
});
