import assert from "assert";
import { isLikelyFundTicker } from "../js/config/assetClasses.js";

async function runTests() {
  let passed = 0;
  let failed = 0;

  console.log("[TEST] Asset Classes Tests\n");
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

  runTest("isLikelyFundTicker handles non-string inputs", () => {
    assert.strictEqual(isLikelyFundTicker(null), false);
    assert.strictEqual(isLikelyFundTicker(undefined), false);
    assert.strictEqual(isLikelyFundTicker(123), false);
    assert.strictEqual(isLikelyFundTicker({}), false);
    assert.strictEqual(isLikelyFundTicker([]), false);
  });

  runTest("isLikelyFundTicker handles empty or whitespace strings", () => {
    assert.strictEqual(isLikelyFundTicker(""), false);
    assert.strictEqual(isLikelyFundTicker("   "), false);
  });

  runTest("isLikelyFundTicker identifies known ETFs from overrides", () => {
    assert.strictEqual(isLikelyFundTicker("VT"), true);
    assert.strictEqual(isLikelyFundTicker("vt"), true); // case insensitive
    assert.strictEqual(isLikelyFundTicker("  VTI  "), true); // handles whitespace
    assert.strictEqual(isLikelyFundTicker("QQQ"), true);
    assert.strictEqual(isLikelyFundTicker("SPY"), true);
  });

  runTest("isLikelyFundTicker identifies likely mutual funds ending in X", () => {
    assert.strictEqual(isLikelyFundTicker("VTSAX"), true); // From overrides and ends in X
    assert.strictEqual(isLikelyFundTicker("ABCDX"), true); // Ends in X, length > 4
    assert.strictEqual(isLikelyFundTicker("abcdx"), true); // case insensitive
  });

  runTest("isLikelyFundTicker rejects non-fund tickers", () => {
    assert.strictEqual(isLikelyFundTicker("AAPL"), false);
    assert.strictEqual(isLikelyFundTicker("MSFT"), false);
    assert.strictEqual(isLikelyFundTicker("X"), false); // too short
    assert.strictEqual(isLikelyFundTicker("ABCX"), false); // not length > 4
  });

  // Summary
  console.log("\n" + "=".repeat(60));
  console.log(`\n[SUMMARY] Results: ${passed} passed, ${failed} failed\n`);

  if (failed > 0) {
    console.log("[ERROR] TESTS FAILED - Asset classes utility has issues\n");
    process.exitCode = 1;
  } else {
    console.log("[SUCCESS] ALL TESTS PASSED - Asset classes utility working correctly");
  }
}

runTests().catch((err) => {
  console.error(err);
  process.exit(1);
});
