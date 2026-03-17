import assert from "assert";

// Mock the DOM environment needed by js/config.js before importing
// Must be global for ES module evaluation phase when using top level imports
global.document = {
  querySelector: () => null
};
global.window = {
  getComputedStyle: () => ({ getPropertyValue: () => "" }),
  matchMedia: () => ({ matches: false })
};

async function runTests() {
  // Use dynamic import so global mocks are established BEFORE module evaluation
  const { getBlueColorForSlice, hexToRgba } = await import("../js/utils/colors.js");

  let passed = 0;
  let failed = 0;

  console.log("[TEST] Colors Utility Tests\n");
  console.log("=".repeat(60));

  const runTest = (name, testFn) => {
    console.log(`\n[CASE] Test: ${name}`);
    try {
      testFn();
      console.log(`   [PASS] ${name}`);
      passed++;
    } catch (e) {
      console.log(`   [FAIL] ${e.message}`);
      failed++;
    }
  };

  runTest("getBlueColorForSlice returns correct color based on index", () => {
    const color0 = getBlueColorForSlice(0);
    assert.strictEqual(typeof color0, "string");
    assert.ok(color0.startsWith("#"));
  });

  runTest("getBlueColorForSlice cycles through palette", () => {
    // There are 8 colors in the palette in config.js:
    // PIE_CHART_SLICE_COLORS: [
    // "#2B2B2B", "#333333", "#4F4F4F", "#606060", "#757575", "#888888", "#A0A0A0", "#BDBDBD"
    // ]
    const color0 = getBlueColorForSlice(0);
    const color8 = getBlueColorForSlice(8);
    const color16 = getBlueColorForSlice(16);

    assert.strictEqual(color0, color8);
    assert.strictEqual(color0, color16);

    const color1 = getBlueColorForSlice(1);
    const color9 = getBlueColorForSlice(9);
    assert.strictEqual(color1, color9);
  });

  runTest("hexToRgba converts 6-digit hex correctly", () => {
    assert.strictEqual(hexToRgba("#FF0000", 0.5), "rgba(255, 0, 0, 0.5)");
    assert.strictEqual(hexToRgba("#00FF00", 1), "rgba(0, 255, 0, 1)");
    assert.strictEqual(hexToRgba("#0000FF", 0), "rgba(0, 0, 255, 0)");
    assert.strictEqual(hexToRgba("#1A2B3C", 0.75), "rgba(26, 43, 60, 0.75)");
  });

  runTest("hexToRgba converts 3-digit hex correctly", () => {
    assert.strictEqual(hexToRgba("#F00", 0.5), "rgba(255, 0, 0, 0.5)");
    assert.strictEqual(hexToRgba("#0F0", 1), "rgba(0, 255, 0, 1)");
    assert.strictEqual(hexToRgba("#00F", 0), "rgba(0, 0, 255, 0)");
    assert.strictEqual(hexToRgba("#123", 0.75), "rgba(17, 34, 51, 0.75)");
  });

  runTest("hexToRgba returns rgba(0, 0, 0, alpha) for invalid hex length", () => {
    assert.strictEqual(hexToRgba("#FF00000", 0.5), "rgba(0, 0, 0, 0.5)");
    assert.strictEqual(hexToRgba("#F0", 1), "rgba(0, 0, 0, 1)");
    assert.strictEqual(hexToRgba("", 0.2), "rgba(0, 0, 0, 0.2)");
  });

  // Summary
  console.log("\n" + "=".repeat(60));
  console.log(`\n[SUMMARY] Results: ${passed} passed, ${failed} failed\n`);

  if (failed > 0) {
    console.log("[ERROR] TESTS FAILED - Colors utility has issues\n");
    process.exit(1);
  } else {
    console.log("[SUCCESS] ALL TESTS PASSED - Colors utility working correctly");
    process.exit(0);
  }
}

runTests().catch(err => {
  console.error(err);
  process.exit(1);
});
