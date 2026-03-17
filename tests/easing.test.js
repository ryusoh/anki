import assert from "assert";
import { easeInOutSine } from "../js/utils/easing.js";

function runTests() {
  let passed = 0;
  let failed = 0;

  console.log("[TEST] Easing Utility Tests\n");
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

  runTest("easeInOutSine evaluates correctly at bounds", () => {
    assert.strictEqual(easeInOutSine(0), 0);
    assert.strictEqual(easeInOutSine(1), 1);
  });

  runTest("easeInOutSine evaluates correctly at midpoints", () => {
    // Math.cos(Math.PI * 0.5) is close to 0 but float precision can vary.
    // val = -(0 - 1) / 2 = 0.5
    const mid = easeInOutSine(0.5);
    assert.ok(mid > 0.499 && mid < 0.501, `Expected close to 0.5, got ${mid}`);
  });

  runTest("easeInOutSine evaluates correctly near bounds", () => {
    const nearStart = easeInOutSine(0.1);
    const nearEnd = easeInOutSine(0.9);

    assert.ok(
      nearStart > 0 && nearStart < 0.5,
      `Expected nearStart to be (0, 0.5), got ${nearStart}`,
    );
    assert.ok(
      nearEnd > 0.5 && nearEnd < 1,
      `Expected nearEnd to be (0.5, 1), got ${nearEnd}`,
    );
    // Symmetric check
    assert.ok(Math.abs(1 - nearEnd - nearStart) < 1e-10, "Should be symmetric");
  });

  // Summary
  console.log("\n" + "=".repeat(60));
  console.log(`\n[SUMMARY] Results: ${passed} passed, ${failed} failed\n`);

  if (failed > 0) {
    console.log("[ERROR] TESTS FAILED - Easing utility has issues\n");
    process.exit(1);
  } else {
    console.log(
      "[SUCCESS] ALL TESTS PASSED - Easing utility working correctly",
    );
    process.exit(0);
  }
}

runTests();
