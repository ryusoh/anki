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

async function testFinalLearningChartFix() {
  try {
    const dom = new JSDOM('<html><body></body></html>', { runScripts: "dangerously" });
    const window = dom.window;
    window.Response = class {
      constructor(body, init) { this.body = body; this.init = init || {}; this.status = this.init.status || 200; this.ok = true; }
      arrayBuffer() { return Promise.resolve(this.body); }
      blob() { return Promise.resolve(new window.Blob([this.body])); }
    };
    window.fetch = function() { return Promise.resolve(new window.Response(new Uint8Array([0]), {})); };
    const scriptContent = fs.readFileSync(INJECTED_JS_PATH, 'utf-8');
    const script = dom.window.document.createElement('script');
    script.textContent = scriptContent;
    dom.window.document.body.appendChild(script);
    const document = window.document;
    function renderLearningChart() {
      document.body.innerHTML = `
        <div class="range-box"><label id="g-year"><input type="radio" value="1">1Y</label><label id="g-all"><input type="radio" value="2">All</label></div>
        <div class="anki-learning-chart-wrapper"><h2 class="chart-header">  学習  </h2><div class="radio-group">
            <label><input type="radio" value="0">1M</label><label><input type="radio" value="1">3M</label>
            <label id="local-year-container"><input type="radio" value="2" id="local-year">1Y</label>
            <label id="local-all-container"><input type="radio" value="3" id="local-all">All</label>
        </div></div>`;
      document.getElementById('g-all').querySelector('input').addEventListener('click', () => { document.getElementById('local-all').checked = true; window.fetch(); });
      document.getElementById('g-year').querySelector('input').addEventListener('click', () => { document.getElementById('local-year').checked = true; window.fetch(); });
    }
    renderLearningChart();
    await new Promise(r => setTimeout(r, 300)); 
    const sixMonthRadio = document.querySelector('[data-six-month-radio]');
    const local1YRadio = document.getElementById('local-year');
    const localAllRadio = document.getElementById('local-all');
    sixMonthRadio.click();
    await new Promise(r => setTimeout(r, 600));
    local1YRadio.checked = true;
    local1YRadio.dispatchEvent(new window.Event('click', { bubbles: true }));
    await new Promise(r => setTimeout(r, 800));
    assert.strictEqual(local1YRadio.checked, true, "1Y radio should be correctly RESTORED");
    assert.strictEqual(localAllRadio.checked, false, "AllTime radio should be UNCHECKED");
    assert.strictEqual(window.__scSixMonthMode, false, "6M mode should be deactivated");
    console.log("Regression Test: Learning Fix passed!");
    process.exit(0);
  } catch (err) { console.error("TEST FAILED:", err); process.exit(1); }
}
testFinalLearningChartFix();
