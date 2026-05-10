/**
 * TDD test: 追加 (Added) chart 6M mode should truncate data beyond 182 days.
 *
 * Bug: In 6-month mode, the 追加 chart shows ALL TIME data instead of
 * only 6 months. Root cause: protobuf int32 negative keys (e.g. -200
 * for "200 days ago") are encoded as 10-byte unsigned varints.
 * decodeVarint overflows JS number precision for these values and
 * `val | 0` returns 0 instead of -200, so the truncation check
 * `keyVal < -182` never triggers.
 *
 * This test builds a mock GraphsResponse protobuf with field 8 (Added)
 * containing entries at day -100 (within 6M) and day -200 (beyond 6M).
 * In 6M mode, day -200 should be truncated (tag rewritten to 0x7a).
 */
import assert from "assert";
import fs from "fs";
import { JSDOM } from "jsdom";
import path from "path";
import { fileURLToPath } from "url";

process.on("uncaughtException", (err) => {
  console.error("FATAL UNCAUGHT EXCEPTION:", err);
  process.exit(1);
});
process.on("unhandledRejection", (err) => {
  console.error("FATAL UNHANDLED REJECTION:", err);
  process.exit(1);
});

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const INJECTED_JS_PATH = path.join(
  __dirname,
  "../stats_page_customizer/injected.js",
);

/**
 * Encode an unsigned varint.
 */
function encodeVarint(val) {
  const bytes = [];
  val = val >>> 0; // treat as unsigned 32-bit
  while (val > 0x7f) {
    bytes.push((val & 0x7f) | 0x80);
    val >>>= 7;
  }
  bytes.push(val & 0x7f);
  return bytes;
}

/**
 * Encode a signed int32 as a protobuf varint (10-byte two's complement).
 */
function encodeSignedVarint(val) {
  if (val >= 0) return encodeVarint(val);
  // Protobuf encodes negative int32 as 10-byte unsigned 64-bit varint
  // (two's complement sign-extended to 64 bits)
  const lo = val >>> 0; // lower 32 bits (unsigned)
  const hi = 0xffffffff; // upper 32 bits (all 1s for negative)
  const bytes = [];
  let loTmp = lo,
    hiTmp = hi;
  for (let i = 0; i < 10; i++) {
    if (i < 4) {
      // Lower 28 bits from lo
      bytes.push(((loTmp & 0x7f) | 0x80) & 0xff);
      loTmp >>>= 7;
    } else if (i === 4) {
      // Straddle: 4 bits from lo, 3 bits from hi
      const combined = ((loTmp & 0x0f) | ((hiTmp & 0x07) << 4)) & 0x7f;
      bytes.push((combined | 0x80) & 0xff);
      hiTmp >>>= 3;
    } else if (i < 9) {
      bytes.push(((hiTmp & 0x7f) | 0x80) & 0xff);
      hiTmp >>>= 7;
    } else {
      bytes.push(hiTmp & 0x7f); // last byte, no continuation
    }
  }
  return bytes;
}

/**
 * Build a protobuf map entry: field 1 = key (varint), field 2 = value (varint).
 */
function buildMapEntry(key, value) {
  const keyBytes = key < 0 ? encodeSignedVarint(key) : encodeVarint(key);
  const valBytes = encodeVarint(value >>> 0);
  // field 1 varint: tag = 0x08, field 2 varint: tag = 0x10
  const inner = [0x08, ...keyBytes, 0x10, ...valBytes];
  // sub-field 1 (map entry): tag = 0x0a, length-delimited
  return [0x0a, inner.length, ...inner];
}

/**
 * Build field 8 (Added) with the given map entries.
 * Field 8, wire type 2 → tag = (8 << 3) | 2 = 0x42
 */
function buildField8(entries) {
  const content = entries.flat();
  return [0x42, ...encodeVarint(content.length), ...content];
}

async function testAddedChart6MTruncation() {
  try {
    const dom = new JSDOM("<html><body></body></html>", {
      runScripts: "dangerously",
    });
    const window = dom.window;
    const document = window.document;

    // Build mock protobuf response:
    // Field 8 (Added) with two entries:
    //   key=-100, value=5  (within 182 days — should be kept)
    //   key=-200, value=3  (beyond 182 days — should be truncated)
    const entry100 = buildMapEntry(-100, 5);
    const entry200 = buildMapEntry(-200, 3);
    const field8 = buildField8([entry100, entry200]);
    const mockResponseBuf = new Uint8Array(field8);

    let capturedResponse = null;

    window.Response = class {
      constructor(body, init) {
        this.body = body;
        this.init = init || {};
        this.status = this.init.status || 200;
        this.ok = true;
        this.headers = null;
        this.statusText = "OK";
      }
      arrayBuffer() {
        return Promise.resolve(this.body);
      }
    };

    window.fetch = function () {
      return Promise.resolve(
        new window.Response(mockResponseBuf.buffer.slice(0), {}),
      ).then(async (res) => {
        const buf = await res.arrayBuffer();
        capturedResponse = new Uint8Array(buf);
        return new window.Response(buf, {});
      });
    };

    // Load injected.js
    const scriptContent = fs.readFileSync(INJECTED_JS_PATH, "utf-8");
    const script = document.createElement("script");
    script.textContent = scriptContent;
    document.body.appendChild(script);

    // Build DOM
    document.body.insertAdjacentHTML(
      "beforeend",
      `<div class="range-box">
        <label><input type="radio" name="range" value="0">M</label>
        <label><input type="radio" name="range" value="1">Y</label>
        <label><input type="radio" name="range" value="2" checked>A</label>
      </div>
      <div class="graph-container"><h2 class="graph-title">追加</h2>
        <div class="radio-group">
          <label><input type="radio" name="added-range" value="0">1M</label>
          <label><input type="radio" name="added-range" value="1">3M</label>
          <label><input type="radio" name="added-range" value="2">1Y</label>
          <label><input type="radio" name="added-range" value="3">All</label>
        </div>
      </div>`,
    );

    // Wire range-box radios to trigger fetch (like Anki does)
    document.querySelector(".range-box").addEventListener("click", (e) => {
      const radio = e.target.closest("input[type='radio']");
      if (radio) window.fetch("/_anki/graphs", { method: "POST", body: new Uint8Array([0x10, 0x01]) });
    });

    await new Promise((r) => setTimeout(r, 400));

    // Verify 6M radio injected on 追加 chart
    const addedContainer = document.querySelector(".graph-container");
    const sixRadio = addedContainer.querySelector("[data-six-month-radio]");
    assert.ok(sixRadio, "6M radio should be injected on 追加 chart");

    // Activate 6M mode
    capturedResponse = null;
    sixRadio.click();
    await new Promise((r) => setTimeout(r, 1500));

    assert.ok(capturedResponse, "Fetch should have been triggered");
    assert.strictEqual(
      window.__scSixMonthMode,
      true,
      "6M mode should be active",
    );

    // Find the entry for key=-200 in the response.
    // If truncation worked, its sub-tag should be rewritten to 0x7a.
    // If NOT truncated, the sub-tag will still be 0x0a.
    //
    // The entry for key=-200 starts AFTER the entry for key=-100.
    // We look for 0x7a in the response to confirm truncation.
    const has0x7a = capturedResponse.includes(0x7a);
    assert.ok(
      has0x7a,
      "BUG: Entry for day=-200 should be truncated (tag 0x7a) in 6M mode, " +
        "but patchGraphsResponse failed to truncate it. " +
        "The 追加 chart shows ALLTIME instead of 6M.",
    );

    // Also verify entry for key=-100 is NOT truncated
    // (it's within 182 days, so its tag should remain 0x0a)
    // The first map entry tag should still be 0x0a
    const field8Start = 2; // after field 8 tag + length
    assert.strictEqual(
      capturedResponse[field8Start],
      0x0a,
      "Entry for day=-100 should NOT be truncated (within 182 days)",
    );

    console.log("Regression Test: 追加 chart 6M truncation passed!");
    if (window.statsCustomizerInterval)
      clearInterval(window.statsCustomizerInterval);
    process.exit(0);
  } catch (err) {
    console.error("TEST FAILED:", err.message);
    process.exit(1);
  }
}

testAddedChart6MTruncation();
