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

async function testFetchBlobResponse() {
  try {
    const dom = new JSDOM('<html><body></body></html>', { runScripts: "dangerously" });
    const window = dom.window;
    window.Response = class {
      constructor(body, init) { this.body = body; this.init = init || {}; this.status = this.init.status || 200; this.ok = true; }
      async arrayBuffer() { return this.body; }
      async blob() { return new window.Blob([this.body]); }
    };
    window.fetch = function() {
      // Field 7 (Future Due)
      // Entry 1: key 180 (within range)
      // Entry 2: key 185 (out of range)
      const mockBuf = new Uint8Array([0x3a, 0x0e, 0x0a, 0x05, 0x08, 0xb4, 0x01, 0x10, 0x05, 0x0a, 0x05, 0x08, 0xb9, 0x01, 0x10, 0x0a]).buffer;
      return Promise.resolve(new window.Response(mockBuf, {}));
    };
    const scriptContent = fs.readFileSync(INJECTED_JS_PATH, 'utf-8');
    const script = dom.window.document.createElement('script');
    script.textContent = scriptContent;
    dom.window.document.body.appendChild(script);
    window.__scSixMonthMode = true;
    const res = await window.fetch("graph", { method: "POST", body: new Uint8Array([0x0a, 0x00]) });
    const blob = await res.blob();
    const buf = await blob.arrayBuffer();
    const arr = new Uint8Array(buf);
    
    // Index 2 is the tag of Entry 1 (0x0a). Should stay 0x0a.
    assert.strictEqual(arr[2], 0x0a, "Entry 1 (180 days) should NOT be truncated");
    // Index 9 is the tag of Entry 2 (0x0a). Should become 0x7a.
    assert.strictEqual(arr[9], 0x7a, "Entry 2 (185 days) SHOULD be truncated");
    
    console.log("Regression Test: Blob Response passed!");
    process.exit(0);
  } catch (err) { console.error("TEST FAILED:", err); process.exit(1); }
}
testFetchBlobResponse();
