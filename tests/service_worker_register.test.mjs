import test, { describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import { JSDOM } from "jsdom";

describe("service_worker_register.js", () => {
  let dom;
  let originalConsoleWarn;
  let registerCalledWith = null;

  beforeEach(() => {
    dom = new JSDOM("<!DOCTYPE html><html><body></body></html>", {
      url: "http://localhost",
    });
    globalThis.window = dom.window;
    globalThis.document = dom.window.document;
    originalConsoleWarn = globalThis.console.warn;
    globalThis.console.warn = () => {};

    registerCalledWith = null;

    dom.window.__SW_FORCE_SW_HOSTNAME__ = "example.com";

    Object.defineProperty(globalThis.navigator, "serviceWorker", {
      configurable: true,
      writable: true,
      value: {
        getRegistrations: () => Promise.resolve([]),
        register: (path, opts) => {
          registerCalledWith = { path, opts };
          return Promise.resolve({
            update: () => Promise.resolve(),
          });
        },
      },
    });
  });

  afterEach(() => {
    delete globalThis.window;
    delete globalThis.document;
    delete globalThis.navigator.serviceWorker;
    globalThis.console.warn = originalConsoleWarn;
  });

  async function withCurrentScript(attributes, callback) {
    const scriptStub = {
      getAttribute: (name) => attributes[name] || null,
    };
    Object.defineProperty(dom.window.document, "currentScript", {
      configurable: true,
      get: () => scriptStub,
    });
    await callback();
    delete dom.window.document.currentScript;
  }

  async function loadScript() {
    await import(`../js/ui/service_worker_register.js?t=${Date.now()}`);
  }

  function triggerLoadImmediately() {
    dom.window.addEventListener = (event, handler) => {
      if (event === "load") {
        handler();
      }
    };
  }

  test("registers service worker with provided attributes", async () => {
    triggerLoadImmediately();
    await withCurrentScript(
      {
        "data-sw-path": "../sw.js",
        "data-sw-scope": "../",
      },
      async () => {
        await loadScript();
      }
    );

    await new Promise((resolve) => setTimeout(resolve, 50));

    assert.ok(registerCalledWith);
    assert.strictEqual(registerCalledWith.path, "../sw.js");
    assert.strictEqual(registerCalledWith.opts.scope, "../");
    assert.strictEqual(registerCalledWith.opts.updateViaCache, "none");
  });

  test("falls back to defaults when attributes missing", async () => {
    triggerLoadImmediately();
    await withCurrentScript({}, async () => {
      await loadScript();
    });

    await new Promise((resolve) => setTimeout(resolve, 50));

    assert.ok(registerCalledWith);
    assert.strictEqual(registerCalledWith.path, "./sw.js");
    assert.strictEqual(registerCalledWith.opts.scope, "./");
  });

  test("does nothing when service workers are unsupported", async () => {
    delete globalThis.navigator.serviceWorker;
    triggerLoadImmediately();
    let listenerAdded = false;
    dom.window.addEventListener = (event) => {
      if (event === "load") listenerAdded = true;
    };

    await withCurrentScript({}, async () => {
      await loadScript();
    });

    await new Promise((resolve) => setTimeout(resolve, 50));
    assert.strictEqual(listenerAdded, false);
  });

  test("ignores registration errors", async () => {
    let warnCalled = false;
    globalThis.console.warn = (msg) => {
      if (msg.includes("Service worker registration failed")) {
        warnCalled = true;
      }
    };

    Object.defineProperty(globalThis.navigator, "serviceWorker", {
      configurable: true,
      value: {
        getRegistrations: () => Promise.resolve([]),
        register: () => Promise.reject(new Error("boom")),
      },
    });

    triggerLoadImmediately();
    await withCurrentScript({}, async () => {
      await loadScript();
    });

    await new Promise((resolve) => setTimeout(resolve, 50));
    assert.strictEqual(warnCalled, true);
  });

  test("ignores sync exceptions thrown inside register callback", async () => {
    let warnCalled = false;
    globalThis.console.warn = (msg) => {
      if (msg.includes("Caught exception calling service worker register")) {
        warnCalled = true;
      }
    };

    Object.defineProperty(globalThis.navigator, "serviceWorker", {
      configurable: true,
      get: () => {
        throw new Error("Sync boom");
      },
    });

    triggerLoadImmediately();
    await withCurrentScript({}, async () => {
      await loadScript();
    });

    await new Promise((resolve) => setTimeout(resolve, 50));
    assert.strictEqual(warnCalled, true);
  });

  test("ignores errors thrown outside registration", async () => {
    let warnCalled = false;
    globalThis.console.warn = (msg) => {
      if (msg.includes("Caught exception initializing service worker")) {
        warnCalled = true;
      }
    };

    Object.defineProperty(dom.window, "__SW_FORCE_SW_HOSTNAME__", {
      get: () => {
        throw new Error("Global IIFE error");
      },
      configurable: true,
    });

    triggerLoadImmediately();
    await withCurrentScript({}, async () => {
      await loadScript();
    });

    await new Promise((resolve) => setTimeout(resolve, 50));
    assert.strictEqual(warnCalled, true);
  });

  test("covers branch where update check fails", async () => {
    let warnCalled = false;
    globalThis.console.warn = (msg) => {
      if (msg.includes("Service worker update check failed")) {
        warnCalled = true;
      }
    };

    Object.defineProperty(globalThis.navigator, "serviceWorker", {
      configurable: true,
      value: {
        getRegistrations: () => Promise.resolve([]),
        register: () =>
          Promise.resolve({
            update: () => Promise.reject(new Error("Update failed")),
          }),
      },
    });

    triggerLoadImmediately();
    await withCurrentScript({}, async () => {
      await loadScript();
    });

    await new Promise((resolve) => setTimeout(resolve, 50));
    assert.strictEqual(warnCalled, true);
  });

  test("covers branch where isLocalHostname returns true directly", async () => {
    dom.window.__SW_FORCE_SW_HOSTNAME__ = "localhost";
    let listenerAdded = false;
    dom.window.addEventListener = () => {
      listenerAdded = true;
    };

    await loadScript();
    assert.strictEqual(listenerAdded, false);
  });

  test("unregisters existing service workers on localhost", async () => {
    dom.window.__SW_FORCE_SW_HOSTNAME__ = "localhost";
    let unregisterCalls = 0;
    const mockUnregister = () => {
      unregisterCalls += 1;
      return Promise.resolve(true);
    };
    let getRegistrationsCalls = 0;
    const mockGetRegistrations = () => {
      getRegistrationsCalls += 1;
      return Promise.resolve([
        { unregister: mockUnregister },
        { unregister: mockUnregister },
      ]);
    };
    Object.defineProperty(globalThis.navigator, "serviceWorker", {
      configurable: true,
      value: { getRegistrations: mockGetRegistrations },
    });

    await loadScript();
    await new Promise((resolve) => setTimeout(resolve, 50));

    assert.strictEqual(getRegistrationsCalls, 1);
    assert.strictEqual(unregisterCalls, 2);
  });

  test("bails out early if serviceWorker is not supported in navigator", async () => {
    dom.window.__SW_FORCE_SW_HOSTNAME__ = "example.com";
    const originalNavigator = globalThis.navigator;
    Object.defineProperty(globalThis, "navigator", {
      value: { userAgent: "node.js" },
      configurable: true,
    });

    let listenerAdded = false;
    dom.window.addEventListener = () => {
      listenerAdded = true;
    };

    await loadScript();
    assert.strictEqual(listenerAdded, false);

    Object.defineProperty(globalThis, "navigator", {
      value: originalNavigator,
      configurable: true,
    });
  });

  test("uses default path and scope when document.currentScript is null", async () => {
    triggerLoadImmediately();
    Object.defineProperty(dom.window.document, "currentScript", {
      configurable: true,
      get: () => null,
    });

    await loadScript();

    await new Promise((resolve) => setTimeout(resolve, 50));

    assert.ok(registerCalledWith);
    assert.strictEqual(registerCalledWith.path, "./sw.js");
    assert.strictEqual(registerCalledWith.opts.scope, "./");
  });

  test("uses window.location.hostname when window.__SW_FORCE_SW_HOSTNAME__ is not string", async () => {
    delete dom.window.__SW_FORCE_SW_HOSTNAME__;
    let listenerAdded = false;
    dom.window.addEventListener = () => {
      listenerAdded = true;
    };

    await loadScript();
    assert.strictEqual(listenerAdded, false);
  });
});
