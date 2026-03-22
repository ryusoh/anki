import assert from "assert";
import {
  isLikelyFundTicker,
  ASSET_CLASS_OVERRIDES,
} from "../js/config/assetClasses.js";

function runTests() {
  let passed = 0;
  let failed = 0;

  console.log("🧪 Asset Classes Utility Tests\n");
  console.log("=".repeat(60));

  const runTest = (name, testFn) => {
    console.log(`\n📋 Test: ${name}`);
    try {
      testFn();
      console.log(`   ✓ ${name}`);
      passed++;
    } catch (e) {
      console.log(`   ✗ ${e.message}`);
      failed++;
    }
  };

  runTest("isLikelyFundTicker returns false for non-string inputs", () => {
    assert.strictEqual(isLikelyFundTicker(null), false);
    assert.strictEqual(isLikelyFundTicker(undefined), false);
    assert.strictEqual(isLikelyFundTicker(123), false);
    assert.strictEqual(isLikelyFundTicker({}), false);
    assert.strictEqual(isLikelyFundTicker([]), false);
  });

  runTest(
    "isLikelyFundTicker returns false for empty or whitespace strings",
    () => {
      assert.strictEqual(isLikelyFundTicker(""), false);
      assert.strictEqual(isLikelyFundTicker("   "), false);
    },
  );

  runTest("isLikelyFundTicker identifies overrides correctly", () => {
    assert.strictEqual(isLikelyFundTicker("VT"), true);
    assert.strictEqual(isLikelyFundTicker("VTI"), true);
    assert.strictEqual(isLikelyFundTicker("VOO"), true);
    assert.strictEqual(isLikelyFundTicker("SPY"), true);
    assert.strictEqual(isLikelyFundTicker("BNDW"), true);
    assert.strictEqual(isLikelyFundTicker("EFA"), true);
  });

  runTest(
    "isLikelyFundTicker identifies overrides case-insensitively and handles whitespace",
    () => {
      assert.strictEqual(isLikelyFundTicker(" vt "), true);
      assert.strictEqual(isLikelyFundTicker("VoO"), true);
      assert.strictEqual(isLikelyFundTicker("\tSPY\n"), true);
    },
  );

  runTest("isLikelyFundTicker identifies mutual funds ending in X", () => {
    assert.strictEqual(isLikelyFundTicker("VTSAX"), true);
    assert.strictEqual(isLikelyFundTicker("FNSFX"), true);
    assert.strictEqual(isLikelyFundTicker("VGSNX"), true);
    assert.strictEqual(isLikelyFundTicker("SWPPX"), true); // Not in overrides, but ends in X and length > 4
    assert.strictEqual(isLikelyFundTicker("FXAIX"), true);
  });

  runTest("isLikelyFundTicker returns false for regular stocks", () => {
    assert.strictEqual(isLikelyFundTicker("AAPL"), false);
    assert.strictEqual(isLikelyFundTicker("MSFT"), false);
    assert.strictEqual(isLikelyFundTicker("GOOGL"), false);
    assert.strictEqual(isLikelyFundTicker("TSLA"), false);
    assert.strictEqual(isLikelyFundTicker("X"), false); // Length not > 4
    assert.strictEqual(isLikelyFundTicker("UBX"), false); // Length not > 4
    assert.strictEqual(isLikelyFundTicker("XOM"), false); // Doesn't end with X
  });

  // Summary
  console.log("\n" + "=".repeat(60));
  console.log(`\n📊 Results: ${passed} passed, ${failed} failed\n`);

  if (failed > 0) {
    console.log("❌ TESTS FAILED - Asset Classes utility has issues\n");
    process.exit(1);
  } else {
    console.log(
      "✅ ALL TESTS PASSED - Asset Classes utility working correctly",
    );
    process.exit(0);
  }
}

runTests();
