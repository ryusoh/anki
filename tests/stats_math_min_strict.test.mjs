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

async function testMathMinStrict() {
  try {
    const dom = new JSDOM('<html><body></body></html>', { runScripts: "dangerously" });
    const scriptContent = fs.readFileSync(INJECTED_JS_PATH, 'utf-8');
    const script = dom.window.document.createElement('script');
    script.textContent = scriptContent;
    dom.window.document.body.appendChild(script);
    const window = dom.window;
    window.__scSixMonthMode = true;
    assert.strictEqual(window.Math.min(70, 182), 182, "Math.min(70, 182) should return 182");
    assert.strictEqual(window.Math.min(182, 70), 182, "Math.min(182, 70) should return 182");
    assert.strictEqual(window.Math.min(70, 200), 70, "Bar widths should be clamped to 70");
    assert.strictEqual(window.Math.min(800, 70), 70, "Bar widths should be clamped to 70");
    console.log("Regression Test: Math.min Strict passed!");
    process.exit(0);
  } catch (err) { console.error("TEST FAILED:", err); process.exit(1); }
}
testMathMinStrict();
