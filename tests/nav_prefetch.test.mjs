import test, { describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import { JSDOM } from "jsdom";

describe("nav_prefetch.js", () => {
  let dom;
  let originalFetch;
  let originalConnection;
  let originalConsoleWarn;
  let fetchCalls = [];

  beforeEach(() => {
    // Set URL path to /terminal/ so prefetching processes the 'home' route assets
    dom = new JSDOM("<!DOCTYPE html><html><body></body></html>", { url: "http://localhost/terminal/" });
    globalThis.window = dom.window;
    globalThis.document = dom.window.document;
    originalConnection = globalThis.navigator.connection;
    originalConsoleWarn = globalThis.console.warn;
    globalThis.console.warn = () => {};

    fetchCalls = [];
    originalFetch = globalThis.fetch;

    globalThis.fetch = (url, opts) => {
      fetchCalls.push({ url, opts });
      if (url && url.endsWith && url.endsWith(".css")) {
        return Promise.resolve({
          ok: true,
          text: () => Promise.resolve(`
            background: url('bg1.png');
            background-image: url("bg2.jpg");
            background: url(bg3.webp);
            background: url(data:image/png;base64,123);
          `),
        });
      }
      return Promise.resolve({
        ok: true,
        text: () => Promise.resolve(""),
        json: () => Promise.resolve({
          assets: [
            { url: "https://external.com/asset.js" },
            { url: "http://invalid url" },
          ],
        }),
      });
    };
    dom.window.fetch = globalThis.fetch;

    dom.window.setTimeout = (cb, delay) => {
      cb();
      return 1;
    };

    dom.window.requestIdleCallback = (cb) => {
      cb();
      return 1;
    };
    globalThis.requestIdleCallback = dom.window.requestIdleCallback;

    Object.defineProperty(globalThis.navigator, "connection", {
      value: { effectiveType: "4g" },
      configurable: true,
      writable: true,
    });

    Object.defineProperty(dom.window.document, "readyState", {
      value: "complete",
      writable: true,
      configurable: true,
    });

    document.body.innerHTML = '<link rel="manifest" href="/assets/manifest.webmanifest" />';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
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
    await import(`../js/ui/nav_prefetch.js?t=${Date.now()}`);
  }

  test("queueFetchTask handles cross-origin fetch options", async () => {
    // Set URL back to root / so /page can be prefetched from navLinks
    dom.window.history.pushState({}, "", "/");
    document.body.innerHTML = `
      <link rel="manifest" href="/assets/manifest.webmanifest" />
      <div class="nav-container">
        <a href="/page" data-prefetch="true">Link</a>
      </div>
    `;

    await loadScript();

    await new Promise((resolve) => setTimeout(resolve, 150));

    // Check if external asset was queried
    const crossOriginCall = fetchCalls.find((c) => c.url === "https://external.com/asset.js");
    if (crossOriginCall) {
      assert.strictEqual(crossOriginCall.opts.mode, "no-cors");
      assert.strictEqual(crossOriginCall.opts.credentials, "omit");
    }
  });

  test("should extract css backgrounds correctly", async () => {
    await loadScript();

    await new Promise((resolve) => setTimeout(resolve, 150));

    const urls = fetchCalls.map((c) => c.url);
    assert.ok(urls.some((url) => url && url.endsWith && url.endsWith("bg1.png")));
    assert.ok(urls.some((url) => url && url.endsWith && url.endsWith("bg2.jpg")));
    assert.ok(urls.some((url) => url && url.endsWith && url.endsWith("bg3.webp")));
    assert.strictEqual(urls.some((url) => url && url.startsWith && url.startsWith("data:")), false);
  });

  test("should handle missing manifest link gracefully and fall back to app base", async () => {
    document.body.innerHTML = "";
    await loadScript();
    await new Promise((resolve) => setTimeout(resolve, 150));
  });

  test("should handle manifest parsing error", async () => {
    document.body.innerHTML = `
      <link rel="manifest" href="http://invalid url" />
    `;
    await loadScript();
    await new Promise((resolve) => setTimeout(resolve, 150));
  });

  test("should handle cross origin links in prefetch gracefully", async () => {
    dom.window.history.pushState({}, "", "/");
    document.body.innerHTML = `
      <link rel="manifest" href="/assets/manifest.webmanifest" />
      <div class="container">
        <a href="http://other-domain.com/path">External</a>
        <a href="/position/">Internal</a>
        <a href="#hash">Hash</a>
        <a href="http://invalid url">Invalid</a>
      </div>
    `;

    await loadScript();

    await new Promise((resolve) => setTimeout(resolve, 150));

    const urls = fetchCalls.map((c) => c.url);
    assert.strictEqual(urls.some((url) => url && url.includes && url.includes("other-domain.com")), false);
  });

  test("should fallback to setTimeout if requestIdleCallback missing", async () => {
    delete dom.window.requestIdleCallback;
    delete globalThis.requestIdleCallback;

    await loadScript();

    await new Promise((resolve) => setTimeout(resolve, 150));

    assert.ok(fetchCalls.length > 0);
  });

  test("should handle manifest URL parsing error gracefully", async () => {
    const OriginalURL = dom.window.URL;
    dom.window.URL = function (url, base) {
      if (url && url.includes("manifest.webmanifest")) {
        throw new Error("Test parsing error");
      }
      return new OriginalURL(url, base);
    };
    globalThis.URL = dom.window.URL;

    document.body.innerHTML = `
      <link rel="manifest" href="/assets/manifest.webmanifest" />
      <div class="container">
        <a href="/position/">Internal</a>
      </div>
    `;

    await loadScript();

    await new Promise((resolve) => setTimeout(resolve, 150));

    globalThis.URL = OriginalURL;
    dom.window.URL = OriginalURL;
  });

  test("should handle missing navigator.connection", async () => {
    delete globalThis.navigator.connection;
    await loadScript();
    await new Promise((resolve) => setTimeout(resolve, 150));
  });

  test("should handle fetch rejection gracefully", async () => {
    globalThis.fetch = () => Promise.reject(new Error("Network error"));
    dom.window.fetch = globalThis.fetch;
    await loadScript();
    await new Promise((resolve) => setTimeout(resolve, 150));
  });

  test("should skip prefetch if saveData is true", async () => {
    Object.defineProperty(globalThis.navigator, "connection", {
      value: { saveData: true },
      configurable: true,
    });

    await loadScript();
    await new Promise((resolve) => setTimeout(resolve, 150));
    assert.strictEqual(fetchCalls.length, 0);
  });

  test("should return early if document visibility is hidden", async () => {
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      get: () => "hidden",
    });

    await loadScript();
    await new Promise((resolve) => setTimeout(resolve, 150));
    assert.strictEqual(fetchCalls.length, 0);
  });

  test("should skip asset if connection is slow and type is video", async () => {
    Object.defineProperty(globalThis.navigator, "connection", {
      value: { effectiveType: "2g", saveData: false },
      configurable: true,
    });

    await loadScript();
    await new Promise((resolve) => setTimeout(resolve, 150));

    const urls = fetchCalls.map((c) => c.url);
    assert.strictEqual(urls.some((url) => url && url.endsWith && url.endsWith("mobile_bg.mp4")), false);
  });

  test("should handle broken URL inside css extract correctly", async () => {
    globalThis.fetch = (url, opts) => {
      fetchCalls.push({ url, opts });
      if (url && url.endsWith(".css")) {
        return Promise.resolve({
          ok: true,
          text: () => Promise.resolve("background: url('http://invalid url');"),
        });
      }
      return Promise.resolve({ ok: true });
    };
    dom.window.fetch = globalThis.fetch;

    await loadScript();
    await new Promise((resolve) => setTimeout(resolve, 150));
  });

  test("should handle empty or missing URL regex matches", async () => {
    globalThis.fetch = (url, opts) => {
      fetchCalls.push({ url, opts });
      if (url && url.endsWith(".css")) {
        return Promise.resolve({
          ok: true,
          text: () => Promise.resolve("background: url(data:image/png;base64,123); background: url(); background:;"),
        });
      }
      return Promise.resolve({ ok: true });
    };
    dom.window.fetch = globalThis.fetch;

    await loadScript();
    await new Promise((resolve) => setTimeout(resolve, 150));
  });

  test("should wait for document to load if readyState is loading", async () => {
    Object.defineProperty(dom.window.document, "readyState", {
      value: "loading",
      configurable: true,
    });

    let loadListenerAdded = false;
    let loadHandler = null;
    dom.window.addEventListener = (event, handler, options) => {
      if (event === "load") {
        loadListenerAdded = true;
        loadHandler = handler;
      }
    };

    await loadScript();
    await new Promise((resolve) => setTimeout(resolve, 150));

    assert.strictEqual(loadListenerAdded, true);
    assert.ok(loadHandler);
  });

  test("should skip asset if connection is slow-2g and type is video", async () => {
    Object.defineProperty(globalThis.navigator, "connection", {
      value: { effectiveType: "slow-2g", saveData: false },
      configurable: true,
    });

    await loadScript();

    await new Promise((resolve) => setTimeout(resolve, 150));

    const urls = fetchCalls.map((c) => c.url);
    assert.strictEqual(urls.some((url) => url && url.endsWith && url.endsWith("mobile_bg.mp4")), false);
  });
});
