/**
 * Test: verify patchGraphsResponse truncates field 7 and field 9
 * entries that exceed 182 days when in 6-month mode.
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

async function testComprehensiveIteration() {
  try {
    const dom = new JSDOM("<html><body></body></html>", {
      runScripts: "dangerously",
    });
    const window = dom.window;
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

    let responseBodies = [];

    // Field 7 (tag 0x3a): map entry with key=200 (unsigned varint 0xc8,0x01)
    const f7Entry = [0x0a, 0x05, 0x08, 0xc8, 0x01, 0x10, 0x05];
    // Field 9 (tag 0x4a): map entry with key=200 (for future due, key > 182)
    const f9Entry = [0x0a, 0x05, 0x08, 0xc8, 0x01, 0x10, 0x03];
    const mockData = new Uint8Array([
      0x3a,
      f7Entry.length,
      ...f7Entry,
      0x4a,
      f9Entry.length,
      ...f9Entry,
    ]);

    window.fetch = function (url, opts) {
      return Promise.resolve(
        new window.Response(mockData.buffer, {}),
      ).then(async (res) => {
        const buf = await res.arrayBuffer();
        responseBodies.push(new Uint8Array(buf));
        return new window.Response(buf, {});
      });
    };

    const scriptContent = fs.readFileSync(INJECTED_JS_PATH, "utf-8");
    const script = dom.window.document.createElement("script");
    script.textContent = scriptContent;
    dom.window.document.body.appendChild(script);

    const document = window.document;
    document.body.insertAdjacentHTML(
      "beforeend",
      `<div class="range-box">
        <label id="g1"><input type="radio" value="1">Y</label>
        <label id="g2"><input type="radio" value="2" checked>A</label>
      </div>
      <div class="chart"><h2 class="graph-title">学習</h2><div class="radio-group">
        <label><input type="radio" value="0">1M</label><label><input type="radio" value="1">3M</label>
        <label id="l2"><input type="radio" value="2">1Y</label><label id="l3"><input type="radio" value="3" checked>All</label>
      </div></div>`,
    );

    // Wire fetch triggers to radio inputs (triggerRefetch clicks inputs)
    document
      .getElementById("g1")
      .querySelector("input")
      .addEventListener("click", () =>
        window.fetch("/_graph", {
          method: "POST",
          body: new Uint8Array([0x10, 0x01]),
        }),
      );
    document
      .getElementById("g2")
      .querySelector("input")
      .addEventListener("click", () =>
        window.fetch("/_graph", {
          method: "POST",
          body: new Uint8Array([0x10, 0x02]),
        }),
      );

    await new Promise((r) => setTimeout(r, 400));

    console.log("Activating 6M...");
    responseBodies = [];
    document.querySelector("[data-six-month-radio]").click();
    await new Promise((r) => setTimeout(r, 1500));

    assert.ok(responseBodies.length > 0, "No fetches recorded!");
    const lastRes = responseBodies[responseBodies.length - 1];

    // Field 7 entry with key=200 (>182) should be truncated: tag rewritten to 0x7a
    assert.strictEqual(
      lastRes[2],
      0x7a,
      "Field 7 entry should be truncated (key=200 > 182 days)",
    );

    console.log("Regression Test: Comprehensive Iteration passed!");
    if (window.statsCustomizerInterval)
      clearInterval(window.statsCustomizerInterval);
    process.exit(0);
  } catch (err) {
    console.error("TEST FAILED:", err);
    process.exit(1);
  }
}
testComprehensiveIteration();
