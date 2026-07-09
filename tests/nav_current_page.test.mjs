import test, { describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import { JSDOM } from "jsdom";

describe("nav_current_page", () => {
  let dom;

  beforeEach(() => {
    dom = new JSDOM("<!DOCTYPE html><html><body></body></html>", { url: "http://localhost" });
    globalThis.window = dom.window;
    globalThis.document = dom.window.document;
    globalThis.location = dom.window.location;
  });

  afterEach(() => {
    delete globalThis.window;
    delete globalThis.document;
    delete globalThis.location;
  });

  const setupLocation = (pathname) => {
    dom.window.history.pushState({}, "", pathname);
  };

  const loadNavCurrentPage = async () => {
    await import(`../js/ui/nav_current_page.js?t=${Date.now()}`);
  };

  const createContainer = (html) => {
    document.body.innerHTML = html;
    document.querySelectorAll("a").forEach((a) => {
      const raw = a.getAttribute("href");
      if (raw && raw.startsWith("/")) {
        Object.defineProperty(a, "href", {
          get: () => {
            return a.hasAttribute("href")
              ? `http://localhost${a.getAttribute("href")}`
              : "";
          },
          configurable: true,
        });
      }
    });
  };

  test("disables link matching current page exact path", async () => {
    setupLocation("/about");
    createContainer(`
      <div class="nav-container">
        <a href="/about" id="about-link">About</a>
        <a href="/contact" id="contact-link">Contact</a>
      </div>
    `);

    await loadNavCurrentPage();

    const aboutLink = document.getElementById("about-link");
    const contactLink = document.getElementById("contact-link");

    assert.strictEqual(aboutLink.hasAttribute("href"), false);
    assert.strictEqual(aboutLink.style.pointerEvents, "none");
    assert.strictEqual(aboutLink.style.cursor, "default");
    assert.strictEqual(aboutLink.getAttribute("aria-current"), "page");
    assert.strictEqual(aboutLink.parentElement.classList.contains("is-current-page"), true);

    assert.strictEqual(contactLink.hasAttribute("href"), true);
    assert.ok(contactLink.style.pointerEvents !== "none");
  });

  test("handles index.html resolution", async () => {
    setupLocation("/");
    createContainer(`
      <div class="container">
        <a href="/index.html" id="home-link">Home</a>
        <a href="/about.html" id="about-link">About</a>
      </div>
    `);

    await loadNavCurrentPage();

    const homeLink = document.getElementById("home-link");
    assert.strictEqual(homeLink.hasAttribute("href"), false);
    assert.strictEqual(homeLink.getAttribute("aria-current"), "page");
  });

  test("handles trailing slash normalization", async () => {
    setupLocation("/analysis/");
    createContainer(`
      <div class="nav-container">
        <a href="/analysis" id="analysis-link">Analysis</a>
      </div>
    `);

    await loadNavCurrentPage();

    const analysisLink = document.getElementById("analysis-link");
    assert.strictEqual(analysisLink.hasAttribute("href"), false);
    assert.strictEqual(analysisLink.getAttribute("aria-current"), "page");
  });

  test("handles path variations of index.html", async () => {
    setupLocation("/analysis/index.html");
    createContainer(`
      <div class="nav-container">
        <a href="/analysis/" id="analysis-link">Analysis</a>
      </div>
    `);

    await loadNavCurrentPage();

    const analysisLink = document.getElementById("analysis-link");
    assert.strictEqual(analysisLink.hasAttribute("href"), false);
    assert.strictEqual(analysisLink.getAttribute("aria-current"), "page");
  });

  test("handles variations when one of them is empty root", async () => {
    setupLocation("/index.html");
    createContainer(`
      <div class="nav-container">
        <a href="/" id="home-link">Home</a>
      </div>
    `);

    await loadNavCurrentPage();

    const homeLink = document.getElementById("home-link");
    assert.strictEqual(homeLink.hasAttribute("href"), false);
    assert.strictEqual(homeLink.getAttribute("aria-current"), "page");
  });

  test("ignores links from different origins", async () => {
    setupLocation("/about");
    createContainer(`
      <div class="nav-container">
        <a href="https://external.com/about" id="external-link">External</a>
      </div>
    `);

    await loadNavCurrentPage();

    const externalLink = document.getElementById("external-link");
    assert.strictEqual(externalLink.hasAttribute("href"), true);
    assert.strictEqual(externalLink.getAttribute("href"), "https://external.com/about");
    assert.ok(externalLink.style.pointerEvents !== "none");
  });

  test("handles links without parent elements safely", async () => {
    setupLocation("/orphan");

    const orphanLink = document.createElement("a");
    orphanLink.href = "/orphan";

    Object.defineProperty(orphanLink, "href", {
      get: () => {
        return orphanLink.hasAttribute("href")
          ? `http://localhost${orphanLink.getAttribute("href")}`
          : "";
      },
      configurable: true,
    });

    assert.strictEqual(orphanLink.parentElement, null);

    const originalQuerySelectorAll = document.querySelectorAll;
    document.querySelectorAll = () => [orphanLink];

    await loadNavCurrentPage();

    assert.strictEqual(orphanLink.hasAttribute("href"), false);
    assert.strictEqual(orphanLink.style.pointerEvents, "none");
    assert.strictEqual(orphanLink.getAttribute("aria-current"), "page");

    document.querySelectorAll = originalQuerySelectorAll;
  });

  test("adds ready listener if document.readyState is loading", async () => {
    setupLocation("/test");

    const originalReadyState = document.readyState;
    Object.defineProperty(document, "readyState", {
      value: "loading",
      writable: true,
      configurable: true,
    });

    createContainer(`
      <div class="nav-container">
        <a href="/test" id="test-link">Test</a>
      </div>
    `);

    await loadNavCurrentPage();

    const testLink = document.getElementById("test-link");
    assert.strictEqual(testLink.hasAttribute("href"), true);

    document.dispatchEvent(new dom.window.Event("DOMContentLoaded"));

    assert.strictEqual(testLink.hasAttribute("href"), false);
    assert.strictEqual(testLink.getAttribute("aria-current"), "page");

    Object.defineProperty(document, "readyState", {
      value: originalReadyState,
      writable: true,
      configurable: true,
    });
  });

  test("handles nav link without parent element gracefully", async () => {
    const standaloneLink = document.createElement("a");
    standaloneLink.className = "nav-link";
    standaloneLink.href = "http://localhost/standalone";

    setupLocation("/standalone");

    const originalQuerySelectorAll = document.querySelectorAll.bind(document);
    document.querySelectorAll = (sel) => {
      if (sel === ".container a, .nav-container a") {
        return [standaloneLink];
      }
      return originalQuerySelectorAll(sel);
    };

    try {
      await loadNavCurrentPage();
      assert.strictEqual(standaloneLink.hasAttribute("href"), false);
      assert.strictEqual(standaloneLink.getAttribute("aria-current"), "page");
    } finally {
      document.querySelectorAll = originalQuerySelectorAll;
    }
  });
});
