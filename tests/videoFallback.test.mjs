import test, { describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import { JSDOM } from "jsdom";

describe("videoFallback.js", () => {
  let dom;
  let container;
  let video;
  let activeTimers = [];
  let originalConsoleWarn;
  let originalSetTimeout;

  beforeEach(() => {
    dom = new JSDOM(`
      <div class="video-background">
        <video poster="custom_poster.jpg"></video>
      </div>
    `, { url: "http://localhost" });

    globalThis.window = dom.window;
    globalThis.document = dom.window.document;

    originalConsoleWarn = globalThis.console.warn;
    globalThis.console.warn = () => {};

    container = document.querySelector(".video-background");
    video = container.querySelector("video");

    // Stub video.play by default
    video.play = () => Promise.resolve();

    activeTimers = [];
    originalSetTimeout = globalThis.setTimeout;
    globalThis.setTimeout = (cb, delay) => {
      activeTimers.push({ cb, delay });
      return activeTimers.length;
    };
    dom.window.setTimeout = globalThis.setTimeout;
  });

  afterEach(() => {
    globalThis.setTimeout = originalSetTimeout;
    globalThis.console.warn = originalConsoleWarn;
    delete globalThis.window;
    delete globalThis.document;
  });

  function advanceTimers(ms) {
    const remaining = [];
    activeTimers.forEach((t) => {
      t.delay -= ms;
      if (t.delay <= 0) {
        t.cb();
      } else {
        remaining.push(t);
      }
    });
    activeTimers = remaining;
  }

  async function runInit() {
    const mod = await import(`../js/ui/videoFallback.js?t=${Date.now()}`);
    mod.initVideoFallback();
  }

  test("does nothing if video container is missing", async () => {
    document.body.innerHTML = "";
    await assert.doesNotReject(runInit);
  });

  test("does nothing if video element is missing inside container", async () => {
    document.body.innerHTML = '<div class="video-background"></div>';
    await assert.doesNotReject(runInit);
  });

  test("uses fallback image from poster when play promise rejects", async () => {
    const playPromise = Promise.reject(new Error("Autoplay prevented"));
    video.play = () => playPromise;

    await runInit();

    // Wait for promise rejection to propagate
    try {
      await playPromise;
    } catch (err) {}
    await Promise.resolve();
    await Promise.resolve();

    assert.strictEqual(video.style.display, "none");
    assert.ok(container.style.backgroundImage.includes("custom_poster.jpg"));
    assert.strictEqual(container.style.backgroundSize, "cover");
    assert.strictEqual(container.style.backgroundPosition, "center center");
    assert.strictEqual(container.style.backgroundRepeat, "no-repeat");
  });

  test("uses default fallback image if poster is not specified", async () => {
    video.removeAttribute("poster");
    const playPromise = Promise.reject(new Error("Autoplay prevented"));
    video.play = () => playPromise;

    await runInit();

    try {
      await playPromise;
    } catch (err) {}
    await Promise.resolve();
    await Promise.resolve();

    assert.ok(container.style.backgroundImage.includes("mobile_bg.jpg"));
  });

  test("handles older browsers without play() promise support via loadstart", async () => {
    video.play = () => undefined; // Simulate old browser returning undefined

    await runInit();

    // Trigger loadstart
    video.dispatchEvent(new dom.window.Event("loadstart"));

    // Simulate video not playing (paused = true)
    Object.defineProperty(video, "paused", { value: true, configurable: true });

    // Advance timers by 1000ms
    advanceTimers(1000);

    assert.strictEqual(video.style.display, "none");
    assert.ok(container.style.backgroundImage.includes("custom_poster.jpg"));
  });

  test("does not apply fallback in older browsers if video is playing", async () => {
    video.play = () => undefined;
    await runInit();

    video.dispatchEvent(new dom.window.Event("loadstart"));

    // Simulate video playing (paused = false, ended = false)
    Object.defineProperty(video, "paused", { value: false, configurable: true });
    Object.defineProperty(video, "ended", { value: false, configurable: true });

    advanceTimers(1000);

    assert.ok(video.style.display !== "none");
    assert.strictEqual(container.style.backgroundImage, "");
  });

  test("applies fallback on video error event", async () => {
    await runInit();

    video.dispatchEvent(new dom.window.Event("error"));

    assert.strictEqual(video.style.display, "none");
    assert.ok(container.style.backgroundImage.includes("custom_poster.jpg"));
  });

  test("applies fallback on video stalled event if video is paused", async () => {
    await runInit();

    video.dispatchEvent(new dom.window.Event("stalled"));

    // Simulate video being paused
    Object.defineProperty(video, "paused", { value: true, configurable: true });

    advanceTimers(2000);

    assert.strictEqual(video.style.display, "none");
    assert.ok(container.style.backgroundImage.includes("custom_poster.jpg"));
  });

  test("does not apply fallback on stalled event if video is still playing", async () => {
    await runInit();

    video.dispatchEvent(new dom.window.Event("stalled"));

    // Simulate video still playing
    Object.defineProperty(video, "paused", { value: false, configurable: true });
    Object.defineProperty(video, "ended", { value: false, configurable: true });

    advanceTimers(2000);

    assert.ok(video.style.display !== "none");
    assert.strictEqual(container.style.backgroundImage, "");
  });
});
