import test, { describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import { JSDOM } from "jsdom";

describe("video_warmup.js", () => {
  let dom;
  let video;
  let originalConnection;
  let originalConsoleWarn;
  let originalFetch;
  let originalCaches;
  let fetchCalls = [];
  let cacheMatchCalls = [];
  let cacheOpenCalls = [];
  let cacheAddCalls = [];
  let setTimeoutCalled = false;
  let requestIdleCallbackCalled = false;

  beforeEach(() => {
    dom = new JSDOM(`
      <div class="video-background">
        <video src="http://example.com/video.mp4"></video>
      </div>
    `, { url: "http://localhost" });

    globalThis.window = dom.window;
    globalThis.document = dom.window.document;
    originalConsoleWarn = globalThis.console.warn;
    globalThis.console.warn = () => {};

    fetchCalls = [];
    cacheMatchCalls = [];
    cacheOpenCalls = [];
    cacheAddCalls = [];
    setTimeoutCalled = false;
    requestIdleCallbackCalled = false;

    originalConnection = globalThis.navigator.connection;
    Object.defineProperty(globalThis.navigator, "connection", {
      writable: true,
      configurable: true,
      value: { effectiveType: "4g", saveData: false },
    });

    dom.window.setTimeout = (cb) => {
      setTimeoutCalled = true;
      cb();
      return 1;
    };

    dom.window.requestIdleCallback = (cb) => {
      requestIdleCallbackCalled = true;
      cb();
      return 1;
    };
    globalThis.requestIdleCallback = dom.window.requestIdleCallback;

    originalFetch = globalThis.fetch;
    globalThis.fetch = (url, opts) => {
      fetchCalls.push({ url, opts });
      return Promise.resolve({ ok: true });
    };
    dom.window.fetch = globalThis.fetch;

    originalCaches = globalThis.caches;
    globalThis.caches = {
      match: (url) => {
        cacheMatchCalls.push(url);
        return Promise.resolve(undefined);
      },
      open: (name) => {
        cacheOpenCalls.push(name);
        return Promise.resolve({
          add: (url) => {
            cacheAddCalls.push(url);
            return Promise.resolve();
          },
        });
      },
    };
    dom.window.caches = globalThis.caches;

    Object.defineProperty(dom.window.document, "readyState", {
      value: "complete",
      configurable: true,
      writable: true,
    });

    video = document.querySelector("video");
    // Mock isConnected to be true
    Object.defineProperty(video, "isConnected", {
      value: true,
      configurable: true,
    });
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    globalThis.caches = originalCaches;
    globalThis.console.warn = originalConsoleWarn;
    if (originalConnection !== undefined) {
      Object.defineProperty(globalThis.navigator, "connection", {
        value: originalConnection,
        configurable: true,
      });
    } else {
      delete globalThis.navigator.connection;
    }
    if (dom && dom.window) {
      dom.window.close();
    }
    delete globalThis.window;
    delete globalThis.document;
    delete globalThis.requestIdleCallback;
  });

  async function loadScript() {
    await import(`../js/ui/video_warmup.js?t=${Date.now()}`);
  }

  test("skips warmup if connection is slow (saveData)", async () => {
    globalThis.navigator.connection.saveData = true;
    await loadScript();
    assert.strictEqual(video.dataset.videoWarmupScheduled, undefined);
  });

  test("ignores connection check if video is present but connection is fast", async () => {
    globalThis.navigator.connection.effectiveType = "4g";
    globalThis.navigator.connection.saveData = false;
    await loadScript();
    assert.strictEqual(video.dataset.videoWarmupScheduled, "true");
  });

  test("uses fallback url correctly when video.currentSrc is available", async () => {
    Object.defineProperty(video, "currentSrc", {
      value: "http://example.com/current_video.mp4",
      configurable: true,
    });
    await loadScript();
    await Promise.resolve(); // flush microtasks
    await Promise.resolve();
    assert.ok(cacheMatchCalls.includes("http://example.com/current_video.mp4"));
  });

  test("skips warmup if connection is fast but using webkitConnection", async () => {
    Object.defineProperty(globalThis.navigator, "connection", {
      value: undefined,
      configurable: true,
    });
    Object.defineProperty(globalThis.navigator, "webkitConnection", {
      value: { effectiveType: "4g", saveData: true },
      configurable: true,
    });
    await loadScript();
    assert.strictEqual(video.dataset.videoWarmupScheduled, undefined);
    delete globalThis.navigator.webkitConnection;
  });

  test("skips warmup if connection is fast but using mozConnection", async () => {
    Object.defineProperty(globalThis.navigator, "connection", {
      value: undefined,
      configurable: true,
    });
    Object.defineProperty(globalThis.navigator, "mozConnection", {
      value: { effectiveType: "2g", saveData: false },
      configurable: true,
    });
    await loadScript();
    assert.strictEqual(video.dataset.videoWarmupScheduled, undefined);
    delete globalThis.navigator.mozConnection;
  });

  test("ignores connection check if navigator.connection is not available", async () => {
    Object.defineProperty(globalThis.navigator, "connection", {
      value: undefined,
      configurable: true,
    });
    await loadScript();
    assert.strictEqual(video.dataset.videoWarmupScheduled, "true");
  });

  test("falls back to fetch if caches.match fails", async () => {
    globalThis.caches.match = (url) => {
      cacheMatchCalls.push(url);
      return Promise.reject(new Error("Cache error"));
    };

    await loadScript();
    await Promise.resolve(); // let catches run
    await Promise.resolve();

    assert.strictEqual(fetchCalls.length, 1);
    assert.strictEqual(fetchCalls[0].url, "http://example.com/video.mp4");
  });

  test("fails warmFetchFallback gracefully", async () => {
    globalThis.fetch = () => Promise.reject(new Error("Fetch failed"));
    delete globalThis.caches;
    delete dom.window.caches;

    await loadScript();
    await Promise.resolve();
    await Promise.resolve();
  });

  test("skips warmup if connection is slow (slow-2g)", async () => {
    globalThis.navigator.connection.effectiveType = "slow-2g";
    await loadScript();
    assert.strictEqual(video.dataset.videoWarmupScheduled, undefined);
  });

  test("ignores playback readiness error during load", async () => {
    video.load = () => {
      throw new Error("Load error");
    };

    let warnCalled = false;
    globalThis.console.warn = (msg) => {
      if (msg.includes("Caught exception:")) {
        warnCalled = true;
      }
    };

    await loadScript();
    await Promise.resolve();
    assert.strictEqual(warnCalled, true);
  });

  test("handles event listener fallback when document is not complete", async () => {
    Object.defineProperty(dom.window.document, "readyState", {
      configurable: true,
      value: "loading",
    });
    let listenerAdded = false;
    let eventName = null;
    dom.window.addEventListener = (event, cb, options) => {
      if (event === "load") {
        listenerAdded = true;
        eventName = event;
      }
    };

    await loadScript();
    assert.strictEqual(listenerAdded, true);
    assert.strictEqual(eventName, "load");
  });

  test("skips warmup if connection is slow (2g)", async () => {
    globalThis.navigator.connection.effectiveType = "2g";
    await loadScript();
    assert.strictEqual(video.dataset.videoWarmupScheduled, undefined);
  });

  test("skips warmup execution if already scheduled", async () => {
    video.dataset.videoWarmupScheduled = "true";
    await loadScript();
    assert.strictEqual(requestIdleCallbackCalled, false);
    assert.strictEqual(setTimeoutCalled, false);
  });

  test("aborts if URL length exceeds 2000 characters", async () => {
    Object.defineProperty(video, "currentSrc", {
      value: "http://example.com/" + "a".repeat(2001) + ".mp4",
      configurable: true,
    });
    await loadScript();
    await Promise.resolve(); // flush microtasks
    await Promise.resolve();
    assert.strictEqual(cacheMatchCalls.length, 0);
  });

  test("handles missing video element gracefully", async () => {
    document.body.innerHTML = "";
    await assert.doesNotReject(loadScript);
  });

  test("schedules warmup using requestIdleCallback", async () => {
    await loadScript();
    assert.strictEqual(video.dataset.videoWarmupScheduled, "true");
    assert.strictEqual(requestIdleCallbackCalled, true);
  });

  test("schedules warmup using setTimeout fallback", async () => {
    delete dom.window.requestIdleCallback;
    delete globalThis.requestIdleCallback;

    await loadScript();
    assert.strictEqual(video.dataset.videoWarmupScheduled, "true");
    assert.strictEqual(setTimeoutCalled, true);
  });

  test("caches the video URL using caches.match and caches.open", async () => {
    await loadScript();
    await Promise.resolve();
    await Promise.resolve();

    assert.ok(cacheMatchCalls.includes("http://example.com/video.mp4"));
    assert.ok(cacheOpenCalls.includes("fund-cache-v1"));
    assert.ok(cacheAddCalls.includes("http://example.com/video.mp4"));
  });

  test("does not cache if video is already cached", async () => {
    globalThis.caches.match = (url) => {
      cacheMatchCalls.push(url);
      return Promise.resolve({}); // Mock already cached
    };
    await loadScript();
    await Promise.resolve();
    await Promise.resolve();

    assert.ok(cacheMatchCalls.includes("http://example.com/video.mp4"));
    assert.strictEqual(cacheOpenCalls.length, 0);
  });

  test("falls back to fetch if caches API add fails", async () => {
    globalThis.caches.open = () => Promise.resolve({
      add: () => Promise.reject(new Error("Cache add error")),
    });

    await loadScript();
    await Promise.resolve();
    await Promise.resolve();

    assert.strictEqual(fetchCalls.length, 1);
  });

  test("updates video.preload to auto and calls load()", async () => {
    video.preload = "none";
    let loadCalled = false;
    video.load = () => {
      loadCalled = true;
    };

    await loadScript();
    assert.strictEqual(video.preload, "auto");
    assert.strictEqual(loadCalled, true);
  });

  test("skips warmup execution if video is not connected", async () => {
    // Override isConnected back to JSDOM default (false since we will remove it)
    Object.defineProperty(video, "isConnected", {
      value: false,
      configurable: true,
    });

    await loadScript();
    await Promise.resolve();

    assert.strictEqual(cacheMatchCalls.length, 0);
  });

  test("skips warmup if readyState implies HAVE_ENOUGH_DATA", async () => {
    Object.defineProperty(video, "readyState", { value: 4, configurable: true });

    await loadScript();
    await Promise.resolve();

    assert.strictEqual(cacheMatchCalls.length, 0);
  });

  test("handles missing src gracefully", async () => {
    video.removeAttribute("src");
    await loadScript();
    await Promise.resolve();
    assert.strictEqual(cacheMatchCalls.length, 0);
  });

  test("evaluates correctly when typeof window is undefined", async () => {
    const originalWindow = globalThis.window;
    delete globalThis.window;

    try {
      await import(`../js/ui/video_warmup.js?t=${Date.now()}`);
    } catch (err) {
      // Ignored: expected error when window is missing
    } finally {
      globalThis.window = originalWindow;
    }
  });
});
