const assert = require("assert");

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

  const { isLikelyFundTicker } = await import("../js/config/assetClasses.js");

  runTest("isLikelyFundTicker basic functionality", () => {
    // These should not throw and return true/false properly
    assert.strictEqual(isLikelyFundTicker("VTSAX"), true);
    assert.strictEqual(isLikelyFundTicker("AAPL"), false);
    assert.strictEqual(isLikelyFundTicker(""), false);
    assert.strictEqual(isLikelyFundTicker("   "), false);
    assert.strictEqual(isLikelyFundTicker(null), false);
    assert.strictEqual(isLikelyFundTicker(123), false);
    assert.strictEqual(isLikelyFundTicker("VFINX"), true);
    assert.strictEqual(isLikelyFundTicker("VTI"), true); // In ASSET_CLASS_OVERRIDES
    // Explicit override cases
    assert.strictEqual(isLikelyFundTicker("BTC"), false);
    assert.strictEqual(isLikelyFundTicker("ETH"), false);
    assert.strictEqual(isLikelyFundTicker("SOL"), false);
    assert.strictEqual(isLikelyFundTicker("USD"), false);
  });

  console.log("\n" + "=".repeat(60));
  console.log(`\n[SUMMARY] Results: ${passed} passed, ${failed} failed\n`);

  if (failed > 0) {
    process.exitCode = 1;
  }
}

runTests().catch((err) => {
  console.error(err);
  process.exit(1);
});
