/**
 * TDD test: 6-month → 1Y selection on 学習 chart.
 *
 * Bug: When the 学習 chart is in 6-month mode and the user clicks "1Y",
 * the selection jumps to "ALLTIME" (value="3") instead of staying on "1Y"
 * (value="2").
 *
 * Root cause theory: When deactivateSixMonthMode bounces the range-box
 * (yearRadio → allRadio), Anki's framework re-syncs per-graph radios
 * to match the range-box. The final range-box click lands on "all",
 * which sets per-graph radios to value="3" (all-time). executeRestore
 * fires after but may be overridden by the framework sync.
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

/**
 * Build a realistic stats page DOM with range-box and 学習 graph.
 * Per-graph radios: 0=month, 1=3months, 2=year(1Y), 3=all_time
 * Range-box radios: 0=month, 1=year, 2=all
 */
function buildStatsPageHTML() {
  return `<html><body>
    <div class="range-box">
      <label><input type="radio" name="range" value="0">M</label>
      <label><input type="radio" name="range" value="1">Y</label>
      <label><input type="radio" name="range" value="2" checked>A</label>
    </div>

    <div class="graph-container">
      <h2 class="graph-title">学習</h2>
      <div class="radio-group">
        <label><input type="radio" name="learn-range" value="0">1M</label>
        <label><input type="radio" name="learn-range" value="1">3M</label>
        <label><input type="radio" name="learn-range" value="2" id="learn-1y">1Y</label>
        <label><input type="radio" name="learn-range" value="3" id="learn-all">All</label>
      </div>
    </div>

    <div class="graph-container">
      <h2 class="graph-title">復習</h2>
      <div class="radio-group">
        <label><input type="radio" name="review-range" value="0">1M</label>
        <label><input type="radio" name="review-range" value="1">3M</label>
        <label><input type="radio" name="review-range" value="2" id="review-1y">1Y</label>
        <label><input type="radio" name="review-range" value="3" id="review-all">All</label>
      </div>
    </div>
  </body></html>`;
}

/**
 * Map range-box value to per-graph value.
 * Range-box: 0=month, 1=year, 2=all
 * Per-graph: 0=month, 1=3months, 2=year, 3=all
 */
function rangeBoxToGraphValue(rbValue) {
  switch (rbValue) {
    case "0":
      return "0"; // month -> month
    case "1":
      return "2"; // year -> year
    case "2":
      return "3"; // all -> all_time
    default:
      return "3";
  }
}

async function test6MonthTo1Y() {
  try {
    const dom = new JSDOM(buildStatsPageHTML(), { runScripts: "dangerously" });
    const window = dom.window;
    const document = window.document;

    // Mock Response
    window.Response = class {
      constructor(body, init) {
        this.body = body;
        this.init = init || {};
        this.status = this.init.status || 200;
        this.ok = true;
      }
      arrayBuffer() {
        return Promise.resolve(this.body);
      }
      blob() {
        return Promise.resolve(new window.Blob([this.body]));
      }
    };

    // Mock fetch
    window.fetch = function () {
      return Promise.resolve(
        new window.Response(new Uint8Array([0]), {}),
      );
    };

    // Simulate Anki's Svelte framework: when range-box radio is clicked,
    // all per-graph radios sync to the corresponding value.
    // This is the crucial behavior that causes the bug.
    const rangeBox = document.querySelector(".range-box");
    rangeBox.addEventListener("click", (e) => {
      const radio = e.target.closest("input[type='radio']");
      if (!radio) return;
      const graphValue = rangeBoxToGraphValue(radio.value);
      // Sync all per-graph radio groups to match
      document.querySelectorAll(".radio-group").forEach((group) => {
        const radios = group.querySelectorAll("input[type='radio']");
        radios.forEach((r) => {
          r.checked = r.value === graphValue;
        });
      });
    });

    // Load the injected script
    const scriptContent = fs.readFileSync(INJECTED_JS_PATH, "utf-8");
    const script = document.createElement("script");
    script.textContent = scriptContent;
    document.body.appendChild(script);

    // Wait for applyChanges() to run and inject 6-month radios
    await new Promise((r) => setTimeout(r, 400));

    // ---- Verify 6-month radio was injected ----
    const learnContainer = document.querySelectorAll(".graph-container")[0];
    const sixMonthRadio = learnContainer.querySelector(
      "[data-six-month-radio]",
    );
    assert.ok(sixMonthRadio, "6-month radio should be injected on 学習 chart");

    // ---- Activate 6-month mode ----
    sixMonthRadio.click();
    await new Promise((r) => setTimeout(r, 800));

    assert.strictEqual(
      window.__scSixMonthMode,
      true,
      "6-month mode should be active",
    );

    // ---- Click "1Y" on the 学習 chart (THE BUG SCENARIO) ----
    const learn1Y = document.getElementById("learn-1y");
    const learnAll = document.getElementById("learn-all");
    assert.ok(learn1Y, "learn-1y radio should exist");

    // Simulate user clicking 1Y
    learn1Y.checked = true;
    learn1Y.dispatchEvent(new window.Event("click", { bubbles: true }));

    // Wait for the full deactivation + bounce + restore sequence
    await new Promise((r) => setTimeout(r, 2000));

    // ---- Verify the result ----
    assert.strictEqual(
      window.__scSixMonthMode,
      false,
      "6-month mode should be deactivated",
    );

    assert.strictEqual(
      learn1Y.checked,
      true,
      "BUG: 1Y radio should be checked after clicking 1Y (got all-time instead)",
    );

    assert.strictEqual(
      learnAll.checked,
      false,
      "BUG: All-time radio should NOT be checked — user clicked 1Y",
    );

    assert.strictEqual(
      sixMonthRadio.checked,
      false,
      "6-month radio should be unchecked",
    );

    console.log(
      "Regression Test: 6-month → 1Y on 学習 chart passed!",
    );

    if (window.statsCustomizerInterval) {
      clearInterval(window.statsCustomizerInterval);
    }
    process.exit(0);
  } catch (err) {
    console.error("TEST FAILED:", err.message);
    process.exit(1);
  }
}

test6MonthTo1Y();
