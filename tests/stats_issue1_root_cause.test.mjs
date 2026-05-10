import assert from 'assert';
import fs from 'fs';
import { JSDOM } from 'jsdom';
import path from 'path';
import { fileURLToPath } from 'url';

// HARDCORE ERROR HANDLERS TO PREVENT HANGING
process.on('uncaughtException', (err) => { 
  console.error("FATAL UNCAUGHT EXCEPTION:", err); 
  process.exit(1); 
});
process.on('unhandledRejection', (err) => { 
  console.error("FATAL UNHANDLED REJECTION:", err); 
  process.exit(1); 
});

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const INJECTED_JS_PATH = path.join(__dirname, '../stats_page_customizer/injected.js');

async function testRootCause() {
  try {
    const dom = new JSDOM('<html><body></body></html>', { runScripts: "dangerously" });
    const scriptContent = fs.readFileSync(INJECTED_JS_PATH, 'utf-8');
    const script = dom.window.document.createElement('script');
    script.textContent = scriptContent;
    dom.window.document.body.appendChild(script);
    const window = dom.window;
    const document = window.document;
    function renderGroup() {
      document.body.innerHTML = `
        <div class="range-box"><label><input type="radio" value="1">Year</label><label><input type="radio" value="2">All</label></div>
        <div class="graph-container"><h2 class="graph-title">Good Graph</h2><div class="radio-group">
            <label><input type="radio" value="0">1M</label><label><input type="radio" value="1">3M</label>
            <label><input type="radio" value="2">1Y</label><label id="all-time-radio"><input type="radio" value="3">AllTime</label>
        </div></div>`;
    }
    renderGroup();
    await new Promise(r => setTimeout(r, 300));
    const sixMonthRadio = document.querySelector('[data-six-month-radio]');
    sixMonthRadio.click();
    await new Promise(r => setTimeout(r, 400));
    assert.strictEqual(window.__scSixMonthMode, true, "Should be in 6M mode");
    renderGroup(); // Simulate Svelte re-render
    await new Promise(r => setTimeout(r, 300));
    const newSixMonthRadio = document.querySelector('[data-six-month-radio]');
    const allTimeRadio = document.getElementById('all-time-radio').querySelector('input');
    assert.strictEqual(window.__scSixMonthMode, true, "6M mode should SURVIVE a DOM re-render!");
    assert.strictEqual(newSixMonthRadio.checked, true, "6M should be checked");
    assert.strictEqual(allTimeRadio.checked, false, "AllTime should be unchecked");
    console.log("Regression Test: Root Cause passed!");
    process.exit(0);
  } catch (err) { console.error("TEST FAILED:", err); process.exit(1); }
}
testRootCause();
