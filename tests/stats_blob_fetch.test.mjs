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

async function testBlobFetch() {
  try {
    const dom = new JSDOM('<html><body></body></html>', { runScripts: "dangerously" });
    const window = dom.window;
    let fetchedBody = null;
    window.fetch = function(url, opts) { fetchedBody = opts.body; return Promise.resolve({ ok: true }); };
    const scriptContent = fs.readFileSync(INJECTED_JS_PATH, 'utf-8');
    const script = dom.window.document.createElement('script');
    script.textContent = scriptContent;
    dom.window.document.body.appendChild(script);
    window.__scSixMonthMode = true;
    const req = new Uint8Array([0x0a, 0x04, 0x74, 0x65, 0x73, 0x74]);
    const blob = new window.Blob([req]);
    await window.fetch("graph", { method: "POST", body: blob });
    await new Promise(r => setTimeout(r, 100));
    if (fetchedBody && fetchedBody.constructor.name === 'Uint8Array') {
      const expected = [0x0a, 0x04, 0x74, 0x65, 0x73, 0x74, 0x10, 0xb6, 0x01];
      assert.deepStrictEqual(Array.from(fetchedBody), expected, "Blob should be patched asynchronously");
    } else { assert.fail("Fetched body was not a patched Uint8Array"); }
    console.log("Regression Test: Blob Fetch passed!");
    process.exit(0);
  } catch (err) { console.error("TEST FAILED:", err); process.exit(1); }
}
testBlobFetch();
