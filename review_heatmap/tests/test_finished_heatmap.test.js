/**
 * Tests for finished-deck heatmap injection
 *
 * The XSS fix (commit f9487096) changed parseMarkup from template.innerHTML
 * to DOMParser.parseFromString. DOMParser moves top-level <script>/<link>
 * into <head> and <div> content into <body>. The original code moved body
 * nodes first, reversing script order: the inline create script (in body)
 * ran before external d3/anki-review-heatmap scripts (in head), causing
 * "ReviewHeatmap is not defined". Fix: move head nodes first.
 */

import { describe, it, expect, beforeEach } from "@jest/globals";
import { JSDOM } from "jsdom";

function buildHeatmapHtml() {
  const WEB_BASE = "/_addons/review_heatmap/web";
  return `
<script type="text/javascript" src="${WEB_BASE}/d3.min.js"></script>
<script type="text/javascript" src="${WEB_BASE}/anki-review-heatmap.js"></script>
<link rel="stylesheet" type="text/css" href="${WEB_BASE}/heatmap-shared.css">

<script>
var rhPlatform = "mac";
var rhNewFinderAPI = false;
</script>

<div class="rh-container rh-view-overview">
<div class="heatmap">
    <div class="heatmap-controls">
        <div class="alignleft"><span>&nbsp;</span></div>
        <div class="aligncenter">
            <div class="hm-btn">prev</div>
            <div class="hm-btn">home</div>
            <div class="hm-btn">next</div>
        </div>
        <div style="clear: both;">&nbsp;</div>
    </div>
    <div id="cal-heatmap"></div>
</div>
<script type="text/javascript">
    window.reviewHeatmap = { created: true };
</script>
</div>
`;
}

// Simulates the fixed parseMarkup (head-first, getAttribute-based)
function parseMarkupHeadFirst(heatmapHtml, domDocument, domWindow) {
  const parser = new domWindow.DOMParser();
  const doc = parser.parseFromString(heatmapHtml, "text/html");
  const fragment = domDocument.createDocumentFragment();
  // Head first to preserve script ordering
  while (doc.head.firstChild) {
    fragment.appendChild(doc.head.firstChild);
  }
  while (doc.body.firstChild) {
    fragment.appendChild(doc.body.firstChild);
  }
  const scripts = [];
  fragment.querySelectorAll("script").forEach((script) => {
    const src = script.getAttribute("src");
    scripts.push({
      src: src || null,
      text: src ? "" : script.textContent || "",
    });
    script.remove();
  });
  const styles = [];
  fragment.querySelectorAll('link[rel="stylesheet"]').forEach((link) => {
    if (link.getAttribute("href")) {
      styles.push(link.getAttribute("href"));
    }
    link.remove();
  });
  return { fragment, scripts, styles };
}

// Simulates the broken parseMarkup (body-first) to document the regression
function parseMarkupBodyFirst(heatmapHtml, domDocument, domWindow) {
  const parser = new domWindow.DOMParser();
  const doc = parser.parseFromString(heatmapHtml, "text/html");
  const fragment = domDocument.createDocumentFragment();
  while (doc.body.firstChild) {
    fragment.appendChild(doc.body.firstChild);
  }
  while (doc.head.firstChild) {
    fragment.appendChild(doc.head.firstChild);
  }
  const scripts = [];
  fragment.querySelectorAll("script").forEach((script) => {
    const src = script.getAttribute("src");
    scripts.push({
      src: src || null,
      text: src ? "" : script.textContent || "",
    });
    script.remove();
  });
  const styles = [];
  fragment.querySelectorAll('link[rel="stylesheet"]').forEach((link) => {
    if (link.getAttribute("href")) {
      styles.push(link.getAttribute("href"));
    }
    link.remove();
  });
  return { fragment, scripts, styles };
}

describe("Finished deck heatmap injection", () => {
  let dom;
  let document;

  beforeEach(() => {
    dom = new JSDOM(
      "<!DOCTYPE html><html><head></head><body><main></main></body></html>",
      { url: "http://127.0.0.1:8080/" },
    );
    document = dom.window.document;
  });

  describe("regression: body-first ordering breaks script execution order", () => {
    it("body-first puts create script BEFORE external scripts", () => {
      const { scripts } = parseMarkupBodyFirst(
        buildHeatmapHtml(),
        document,
        dom.window,
      );
      const createIdx = scripts.findIndex(
        (s) => s.text && s.text.includes("reviewHeatmap"),
      );
      const d3Idx = scripts.findIndex((s) => s.src && s.src.includes("d3.min"));
      const hmIdx = scripts.findIndex(
        (s) => s.src && s.src.includes("anki-review-heatmap"),
      );

      // Broken: create runs before its dependencies are loaded
      expect(createIdx).toBeLessThan(d3Idx);
      expect(createIdx).toBeLessThan(hmIdx);
    });
  });

  describe("fix: head-first ordering preserves correct script order", () => {
    it("external scripts come BEFORE inline create script", () => {
      const { scripts } = parseMarkupHeadFirst(
        buildHeatmapHtml(),
        document,
        dom.window,
      );
      const createIdx = scripts.findIndex(
        (s) => s.text && s.text.includes("reviewHeatmap"),
      );
      const d3Idx = scripts.findIndex((s) => s.src && s.src.includes("d3.min"));
      const hmIdx = scripts.findIndex(
        (s) => s.src && s.src.includes("anki-review-heatmap"),
      );

      expect(d3Idx).toBeLessThan(createIdx);
      expect(hmIdx).toBeLessThan(createIdx);
    });

    it("extracts correct number of scripts and styles", () => {
      const { scripts, styles } = parseMarkupHeadFirst(
        buildHeatmapHtml(),
        document,
        dom.window,
      );
      expect(scripts.length).toBe(4);
      expect(styles.length).toBe(1);

      const externalScripts = scripts.filter((s) => s.src !== null);
      const inlineScripts = scripts.filter((s) => s.src === null);
      expect(externalScripts.length).toBe(2);
      expect(inlineScripts.length).toBe(2);
    });

    it("external script srcs are correct paths", () => {
      const { scripts } = parseMarkupHeadFirst(
        buildHeatmapHtml(),
        document,
        dom.window,
      );
      const externalScripts = scripts.filter((s) => s.src !== null);
      expect(externalScripts[0].src).toBe(
        "/_addons/review_heatmap/web/d3.min.js",
      );
      expect(externalScripts[1].src).toBe(
        "/_addons/review_heatmap/web/anki-review-heatmap.js",
      );
    });

    it("inline scripts contain expected content", () => {
      const { scripts } = parseMarkupHeadFirst(
        buildHeatmapHtml(),
        document,
        dom.window,
      );
      const inlineScripts = scripts.filter((s) => s.src === null);
      expect(inlineScripts[0].text).toContain("rhPlatform");
      expect(inlineScripts[1].text).toContain("reviewHeatmap");
    });
  });

  describe("DOM structure after mounting", () => {
    it("preserves #cal-heatmap and controls in fragment", () => {
      const { fragment } = parseMarkupHeadFirst(
        buildHeatmapHtml(),
        document,
        dom.window,
      );
      expect(fragment.querySelector("#cal-heatmap")).not.toBeNull();
      expect(fragment.querySelector(".heatmap-controls")).not.toBeNull();
      expect(fragment.querySelector(".rh-container")).not.toBeNull();
    });

    it("#cal-heatmap findable via document.querySelector after mounting", () => {
      const { fragment } = parseMarkupHeadFirst(
        buildHeatmapHtml(),
        document,
        dom.window,
      );

      const container = document.createElement("div");
      container.id = "review-heatmap-finished";
      document.querySelector("main").appendChild(container);
      container.textContent = "";
      container.appendChild(fragment);

      expect(document.querySelector("#cal-heatmap")).not.toBeNull();
      expect(document.querySelector(".heatmap-controls")).not.toBeNull();
    });
  });
});
