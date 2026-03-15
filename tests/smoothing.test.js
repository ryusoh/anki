import assert from "assert";
import {
  simpleMovingAverage,
  exponentialMovingAverage,
  savitzkyGolay,
  lowess,
  adaptiveSmoothing,
  smoothFinancialData,
  SMOOTHING_CONFIGS
} from "../js/utils/smoothing.js";

function runTests() {
  let passed = 0;
  let failed = 0;

  console.log("🧪 Smoothing Utility Tests\n");
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

  const sampleData = [
    { x: 1, y: 10 },
    { x: 2, y: 20 },
    { x: 3, y: 30 },
    { x: 4, y: 40 },
    { x: 5, y: 50 },
  ];

  runTest("simpleMovingAverage handles empty or small data", () => {
    assert.deepStrictEqual(simpleMovingAverage([]), []);
    assert.deepStrictEqual(simpleMovingAverage(null), null);
    assert.deepStrictEqual(simpleMovingAverage("not array"), "not array");

    const smallData = [{ x: 1, y: 10 }, { x: 2, y: 20 }];
    assert.deepStrictEqual(simpleMovingAverage(smallData, 3), smallData, "Returns original data if length < window");
  });

  runTest("simpleMovingAverage computes correct averages", () => {
    const result = simpleMovingAverage(sampleData, 3, false);

    assert.strictEqual(result.length, 5);
    assert.strictEqual(result[0].y, 20);
    assert.strictEqual(result[1].y, 20);
    assert.strictEqual(result[2].y, 30);
    assert.strictEqual(result[3].y, 40);
    assert.strictEqual(result[4].y, 45);
  });

  runTest("simpleMovingAverage preserves last point when requested", () => {
    const result = simpleMovingAverage(sampleData, 3, true);

    assert.strictEqual(result.length, 5);
    assert.strictEqual(result[4].y, 50, "Last point should remain unchanged");
    assert.notStrictEqual(result[4], sampleData[4], "Should return a copy, not a reference");
  });

  runTest("exponentialMovingAverage handles empty or small data", () => {
    assert.deepStrictEqual(exponentialMovingAverage([]), []);
    const singleElement = [{ x: 1, y: 10 }];
    assert.deepStrictEqual(exponentialMovingAverage(singleElement), singleElement);
  });

  runTest("exponentialMovingAverage computes correct values", () => {
    const alpha = 0.5;
    const result = exponentialMovingAverage(sampleData, alpha, false);

    assert.strictEqual(result[0].y, 10);
    // index 1: alpha * 20 + (1-alpha) * 10 = 0.5*20 + 0.5*10 = 15
    assert.strictEqual(result[1].y, 15);
    // index 2: 0.5*30 + 0.5*15 = 15 + 7.5 = 22.5
    assert.strictEqual(result[2].y, 22.5);
  });

  runTest("smoothFinancialData applies correct configuration", () => {
    // Basic test to ensure the main export function orchestrates correctly
    const result = smoothFinancialData(sampleData, "balanced", false);

    assert.strictEqual(result.length, 5);
    // First point should be unchanged by EMA
    assert.strictEqual(result[0].y, 10);
    // Should be smoothed, EMA with alpha 0.3
    const expectedSecondY = 0.3 * 20 + 0.7 * 10; // 6 + 7 = 13
    assert.strictEqual(result[1].y, expectedSecondY);
  });

  // Summary
  console.log("\n" + "=".repeat(60));
  console.log(`\n📊 Results: ${passed} passed, ${failed} failed\n`);

  if (failed > 0) {
    console.log("❌ TESTS FAILED - Smoothing utility has issues\n");
    process.exit(1);
  } else {
    console.log("✅ ALL TESTS PASSED - Smoothing utility working correctly");
  }
}

runTests();
