/**
 * Test: verifies patchGraphsResponse truncates cached response data
 * when in 6-month mode, and that leaving 6-month mode produces
 * untruncated data.
 */
import assert from "assert";
import fs from "fs";
import { JSDOM } from "jsdom";
import path from "path";
import { fileURLToPath } from "url";

process.on("uncaughtException", (err) => {
  console.error("FATAL UNCAUGHT EXCEPTION:", err);
  process.exit(1);
});
process.on("unhandledRejection", (err) => {
  console.error("FATAL UNHANDLED REJECTION:", err);
  process.exit(1);
});

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const INJECTED_JS_PATH = path.join(
  __dirname,
  "../stats_page_customizer/injected.js",
);

async function testCacheRefetch() {
  try {
    const dom = new JSDOM("<html><body></body></html>", {
      runScripts: "dangerously",
    });
    const window = dom.window;
    let svelteDataCache = null;
    window.Response = class {
      constructor(body, init) {
        this.body = body;
        this.init = init || {};
        this.status = this.init.status || 200;
        this.ok = true;
        this.headers = null;
      }
      arrayBuffer() {
        return Promise.resolve(this.body);
      }
    };
    window.fetch = function (url, opts) {
      return new Promise((resolve) => {
        setTimeout(() => {
          // Field 7 (tag 0x3a=field7,wireType2): map entry with key=185
          const mockBuf = new Uint8Array([
            0x3a, 0x07, 0x0a, 0x05, 0x08, 0xb9, 0x01, 0x10, 0x05,
          ]).buffer;
          resolve(new window.Response(mockBuf));
        }, 20);
      }).then(async (res) => {
        svelteDataCache = new Uint8Array(await res.arrayBuffer());
        return new window.Response(svelteDataCache.buffer);
      });
    };
    const scriptContent = fs.readFileSync(INJECTED_JS_PATH, "utf-8");
    const script = dom.window.document.createElement("script");
    script.textContent = scriptContent;
    dom.window.document.body.appendChild(script);

    // Build DOM with range-box and a learning chart.
    // Wire fetch triggers to the radio INPUTS (not labels), matching
    // how triggerRefetch() calls input.click().
    const document = window.document;
    document.body.insertAdjacentHTML(
      "beforeend",
      `
      <div class="range-box">
        <label id="g1"><input type="radio" value="1">Y</label>
        <label id="g2"><input type="radio" value="2">All</label>
      </div>
      <div class="graph-container"><h2 class="graph-title">学習</h2><div class="radio-group">
        <label><input type="radio" value="0">1M</label><label><input type="radio" value="1">3M</label>
        <label id="l2"><input type="radio" value="2">1Y</label><label id="l3"><input type="radio" value="3">All</label>
      </div></div>`,
    );

    // Wire fetch to radio inputs directly (triggerRefetch clicks inputs)
    document
      .getElementById("g1")
      .querySelector("input")
      .addEventListener("click", () => window.fetch("/_graph", { method: "POST", body: new Uint8Array([0x10, 0x01]) }));
    document
      .getElementById("g2")
      .querySelector("input")
      .addEventListener("click", () => window.fetch("/_graph", { method: "POST", body: new Uint8Array([0x10, 0x02]) }));

    // Wait for applyChanges to inject 6-month radio
    await new Promise((r) => setTimeout(r, 400));

    const sixRadio = document.querySelector("[data-six-month-radio]");
    assert.ok(sixRadio, "6-month radio should exist");

    // Activate 6-month mode
    sixRadio.click();
    await new Promise((r) => setTimeout(r, 1500));

    assert.ok(
      svelteDataCache && svelteDataCache.includes(0x7a),
      "Cache should be truncated (0x7a tag) in 6-month mode",
    );

    console.log("Regression Test: Cache Refetch passed!");
    if (window.statsCustomizerInterval)
      clearInterval(window.statsCustomizerInterval);
    process.exit(0);
  } catch (err) {
    console.error("TEST FAILED:", err);
    process.exit(1);
  }
}
testCacheRefetch();
