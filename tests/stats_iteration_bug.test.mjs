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

async function testIterationBug() {
  try {
    const dom = new JSDOM('<html><body></body></html>', { runScripts: "dangerously" });
    const window = dom.window;
    window.Response = class { constructor(body, init) { this.body = body; } arrayBuffer() { return Promise.resolve(this.body); } };
    let lastRequestDays = 0;
    window.fetch = function(url, opts) {
        if (opts && opts.body) {
            const arr = new Uint8Array(opts.body);
            for(let i=0; i<arr.length; i++) if(arr[i]===0x10) {
                let val=0, shift=0; i++;
                while(i<arr.length) { val |= (arr[i]&0x7f)<<shift; if(!(arr[i]&0x80)) break; shift+=7; i++; }
                lastRequestDays = val;
            }
        }
        return Promise.resolve(new window.Response(new Uint8Array([0x3a, 0x00]).buffer));
    };
    const scriptContent = fs.readFileSync(INJECTED_JS_PATH, 'utf-8');
    const script = dom.window.document.createElement('script');
    script.textContent = scriptContent;
    dom.window.document.body.appendChild(script);
    const document = window.document;
    document.body.innerHTML = `
      <div class="range-box"><label id="g1"><input type="radio" value="1">Y</label><label id="g2"><input type="radio" value="2" checked>A</label></div>
      <div class="chart"><h2 class="graph-title">学習</h2><div class="radio-group"><label id="l0"><input type="radio" value="0">1M</label><label id="l1"><input type="radio" value="1">3M</label><label id="l2"><input type="radio" value="2">1Y</label><label id="l3"><input type="radio" value="3" checked>All</label></div></div>`;
    // Svelte behavior mock: keep the same radio-group element across re-renders
    const radioGroup = document.querySelector('.radio-group');
    function mockSvelteFetch() {
       window.fetch("graph", { method: "POST", body: new Uint8Array([0x0a, 0x00]) });
    }
    radioGroup.querySelectorAll('input').forEach(inp => inp.addEventListener('click', mockSvelteFetch));

    await new Promise(r => setTimeout(r, 300));
    const get6M = () => document.querySelector('[data-six-month-radio]');
    
    console.log("Step 1: Clicking 1Y (6M mode off)");
    document.getElementById('l2').querySelector('input').click();
    await new Promise(r => setTimeout(r, 800));
    assert.strictEqual(window.__scSixMonthMode, false);

    console.log("Step 2: Clicking AllTime (6M mode off)");
    document.getElementById('l3').querySelector('input').click();
    await new Promise(r => setTimeout(r, 800));
    assert.strictEqual(window.__scSixMonthMode, false);
    
    console.log("Step 3: Activating 6M");
    lastRequestDays = 0;
    get6M().click();
    await new Promise(r => setTimeout(r, 1200));

    console.log("Final lastRequestDays:", lastRequestDays);
    assert.strictEqual(lastRequestDays, 182, "Should have fetched 182 days even after iteration!");

    console.log("New Bug Test: Iteration Sync passed!");
    process.exit(0);
  } catch (err) { console.error("TEST FAILED:", err); process.exit(1); }
}
testIterationBug();
