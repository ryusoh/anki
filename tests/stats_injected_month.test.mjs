import assert from 'assert';
import fs from 'fs';
import { JSDOM } from 'jsdom';
import path from 'path';
import { fileURLToPath } from 'url';

process.on('uncaughtException', (err) => { console.error("FATAL UNCAUGHT EXCEPTION:", err); process.exit(1); });
process.on('unhandledRejection', (err) => { console.error("FATAL UNHANDLED REJECTION:", err); process.exit(1); });

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const INJECTED_JS_PATH = path.join(__dirname, '../stats_page_customizer/injected.js');

function testMonthHiding() {
  const html = `<html><body>
    <div class="range-box"><label><input type="radio" value="1">Y</label><label><input type="radio" value="2">A</label></div>
    <div class="graph-container"><h2 class="graph-title">復習間隔</h2><div class="radio-group">
      <label id="m"><input type="radio" value="0">M</label><label><input type="radio" value="1">3</label>
      <label><input type="radio" value="2">Y</label><label><input type="radio" value="3">A</label>
    </div></div>
  </body></html>`;
  const dom = new JSDOM(html, { runScripts: "dangerously" });
  const scriptContent = fs.readFileSync(INJECTED_JS_PATH, 'utf-8');
  const script = dom.window.document.createElement('script');
  script.textContent = scriptContent;
  dom.window.document.body.appendChild(script);
  const document = dom.window.document;
  setTimeout(() => {
    const m = document.getElementById('m');
    assert.strictEqual(m.style.display, 'none', "Month should be hidden in intervals");
    console.log("Regression Test: Month Hiding passed!");
    process.exit(0);
  }, 500);
}
testMonthHiding();
