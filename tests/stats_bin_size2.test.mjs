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

function testBinSize() {
  const dom = new JSDOM('<html><body></body></html>', { runScripts: "dangerously" });
  const window = dom.window;
  const scriptContent = fs.readFileSync(INJECTED_JS_PATH, 'utf-8');
  const script = window.document.createElement('script');
  script.textContent = scriptContent;
  window.document.body.appendChild(script);
  window.__scSixMonthMode = true;
  for (let dataLength = 71; dataLength <= 183; dataLength++) {
    const maxDays = window.Math.min(70, dataLength);
    assert.strictEqual(maxDays, dataLength, `maxDays should be unclamped for ${dataLength}`);
  }
  console.log("Regression Test: Bin Size passed!");
  process.exit(0);
}
testBinSize();
