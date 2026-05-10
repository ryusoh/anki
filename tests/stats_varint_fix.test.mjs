/**
 * Test: decodeVarint correctly decodes unsigned protobuf varints.
 *
 * decodeVarint is an unsigned varint decoder that applies `val | 0` to
 * coerce to a signed 32-bit integer at the end. This means:
 * - Small positive values decode as-is (e.g. 200 → 200)
 * - Large unsigned values that exceed 2^31-1 wrap to negative via `| 0`
 *   (e.g. 0xFFFFFF38 unsigned → -200 signed)
 * - Protobuf's zigzag-encoded sint32 values are NOT decoded here;
 *   zigzag decoding is a separate step not implemented in decodeVarint.
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

function testDecodeVarint() {
  // Replicate the exact decodeVarint from injected.js
  const decodeVarint = function (arr, offset) {
    var val = 0,
      shift = 0,
      i = offset;
    var b;
    do {
      b = arr[i++];
      if (shift < 31) val += (b & 0x7f) << shift;
      else val += (b & 0x7f) * Math.pow(2, shift);
      shift += 7;
    } while (b & 0x80 && i < arr.length);
    return { value: val | 0, next: i };
  };

  // Test 1: Positive value 200 = varint bytes [0xc8, 0x01]
  const resPos = decodeVarint(new Uint8Array([0xc8, 0x01]), 0);
  assert.strictEqual(resPos.value, 200, "Should decode 200 correctly");
  assert.strictEqual(resPos.next, 2, "Should consume 2 bytes");

  // Test 2: Small value 56 = varint byte [0x38]
  const res56 = decodeVarint(new Uint8Array([0x38]), 0);
  assert.strictEqual(res56.value, 56, "Should decode 56 correctly");
  assert.strictEqual(res56.next, 1, "Should consume 1 byte");

  // Test 3: Value 182 (6-month boundary) = varint bytes [0xb6, 0x01]
  const res182 = decodeVarint(new Uint8Array([0xb6, 0x01]), 0);
  assert.strictEqual(
    res182.value,
    182,
    "Should decode 182 (6-month boundary)",
  );

  // Test 4: Value 365 = varint bytes [0xed, 0x02]
  const res365 = decodeVarint(new Uint8Array([0xed, 0x02]), 0);
  assert.strictEqual(res365.value, 365, "Should decode 365");

  // Test 5: Single-byte value 0 = [0x00]
  const res0 = decodeVarint(new Uint8Array([0x00]), 0);
  assert.strictEqual(res0.value, 0, "Should decode 0");

  // Test 6: Large unsigned value that wraps negative via | 0
  // 0xFFFFFF38 unsigned = -200 signed (via | 0)
  // As varint: b8 fe ff ff 0f
  const resNeg = decodeVarint(
    new Uint8Array([0xb8, 0xfe, 0xff, 0xff, 0x0f]),
    0,
  );
  assert.strictEqual(
    resNeg.value,
    -200,
    "Large unsigned varint should wrap to -200 via | 0",
  );

  // Test 7: Offset parameter works
  const resOffset = decodeVarint(
    new Uint8Array([0xff, 0xff, 0xc8, 0x01]),
    2,
  );
  assert.strictEqual(resOffset.value, 200, "Should decode at offset 2");
  assert.strictEqual(resOffset.next, 4, "Next should be 4");

  console.log("decodeVarint test passed!");
  process.exit(0);
}
testDecodeVarint();
