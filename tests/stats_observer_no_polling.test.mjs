import test from "node:test";
import assert from "node:assert";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { JSDOM } from "jsdom";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const INJECTED_JS_PATH = path.join(
  __dirname,
  "../stats_page_customizer/injected.js",
);

function createStatsHtml() {
  return `<html><body>
    <div class="range-box"><label><input type="radio" value="1">Y</label><label><input type="radio" value="2">A</label></div>
    <div class="graph-container"><h2 class="graph-title">Test</h2><div class="radio-group">
      <label><input type="radio" value="0">M</label><label><input type="radio" value="1">3</label>
      <label><input type="radio" value="2">Y</label><label><input type="radio" value="3">A</label>
    </div></div>
  </body></html>`;
}

test("injected.js uses MutationObserver instead of setInterval polling", async () => {
  const dom = new JSDOM(createStatsHtml(), { runScripts: "dangerously" });
  let setIntervalCalls = 0;
  dom.window.setInterval = () => {
    setIntervalCalls += 1;
    return 999;
  };

  const scriptContent = fs.readFileSync(INJECTED_JS_PATH, "utf8");
  const script = dom.window.document.createElement("script");
  script.textContent = scriptContent;
  dom.window.document.body.appendChild(script);

  assert.strictEqual(setIntervalCalls, 0);
  assert.strictEqual(dom.window.statsCustomizerInterval, null);
  assert.ok(dom.window.statsCustomizerObserver);

  const initialLabels = Array.from(
    dom.window.document.querySelectorAll("label"),
  );
  assert.ok(initialLabels.some((l) => l.textContent.includes("6か月")));

  const added = dom.window.document.createElement("div");
  added.className = "graph-container";
  added.innerHTML =
    '<h2 class="graph-title">Added Graph</h2><div class="radio-group">' +
    '<label><input type="radio" value="0">M</label>' +
    '<label><input type="radio" value="1">3</label>' +
    '<label><input type="radio" value="2">Y</label>' +
    '<label><input type="radio" value="3">A</label></div>';
  dom.window.document.body.appendChild(added);

  await new Promise((resolve) => setTimeout(resolve, 80));

  const addedLabels = Array.from(added.querySelectorAll("label"));
  assert.ok(
    addedLabels.some((l) => l.textContent.includes("6か月")),
    "dynamically inserted graph should receive 6か月 via MutationObserver",
  );
  dom.window.statsCustomizerObserver.disconnect();
});
