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

async function test1YHalfData() {
  try {
    const dom = new JSDOM('<html><body></body></html>', { runScripts: "dangerously" });
    const window = dom.window;
    window.Response = class { constructor(body, init) { this.body = body; this.init = init; } arrayBuffer() { return Promise.resolve(this.body); } };
    let interceptedFetches = 0;
    window.fetch = function(url, opts) {
      if (opts && opts.body && opts.body.length > 0 && opts.body[opts.body.length-2] === 0xb6) interceptedFetches++;
      return Promise.resolve(new window.Response(new Uint8Array([0]).buffer, {}));
    };
    const scriptContent = fs.readFileSync(INJECTED_JS_PATH, 'utf-8');
    const script = dom.window.document.createElement('script');
    script.textContent = scriptContent;
    dom.window.document.body.appendChild(script);
    const document = window.document;
    document.body.innerHTML = `<div class="range-box"><label id="g1"><input type="radio" value="1">Y</label></div>
      <div class="graph-container"><h2 class="graph-title">学習</h2><div class="radio-group">
      <label><input type="radio" value="0">1M</label><label><input type="radio" value="1">3M</label><label id="l2"><input type="radio" value="2">1Y</label><label><input type="radio" value="3">A</label>
      </div></div>`;
    document.getElementById('l2').querySelector('input').addEventListener('click', () => { window.fetch("graph", { method: "POST", body: new Uint8Array([0x0a, 0x00]) }); });
    await new Promise(r => setTimeout(r, 300));
    const sixM = document.querySelector('[data-six-month-radio]');
    const target1Y = document.getElementById('l2').querySelector('input');
    sixM.click();
    await new Promise(r => setTimeout(r, 600));
    interceptedFetches = 0;
    target1Y.click();
    await new Promise(r => setTimeout(r, 100));
    assert.strictEqual(interceptedFetches, 0, "Fetch should NOT be intercepted after clicking 1Y");
    console.log("Regression Test: 1Y Half Data passed!");
    process.exit(0);
  } catch (err) { console.error("TEST FAILED:", err); process.exit(1); }
}
test1YHalfData();
