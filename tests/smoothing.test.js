import assert from "assert";
import {
  simpleMovingAverage,
  exponentialMovingAverage,
  savitzkyGolay,
  lowess,
  adaptiveSmoothing,
  smoothFinancialData,
  SMOOTHING_CONFIGS,
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

    const smallData = [
      { x: 1, y: 10 },
      { x: 2, y: 20 },
    ];
    assert.deepStrictEqual(
      simpleMovingAverage(smallData, 3),
      smallData,
      "Returns original data if length < window",
    );
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
    assert.notStrictEqual(
      result[4],
      sampleData[4],
      "Should return a copy, not a reference",
    );
  });

  runTest("exponentialMovingAverage handles empty or small data", () => {
    assert.deepStrictEqual(exponentialMovingAverage([]), []);
    const singleElement = [{ x: 1, y: 10 }];
    assert.deepStrictEqual(
      exponentialMovingAverage(singleElement),
      singleElement,
    );
  });

  runTest("exponentialMovingAverage computes correct values", () => {
    const alpha = 0.5;
    const result = exponentialMovingAverage(sampleData, alpha, false);

    assert.strictEqual(result[0].y, 10);
    // index 1: alpha * 20 + (1-alpha) * 10 = 0.5*20 + 0.5*10 = 15
    assert.strictEqual(result[1].y, 15);
    // index 2: 0.5*30 + 0.5*15 = 15 + 7.5 = 22.5
    assert.strictEqual(result[2].y, 22.5);

    // Hit lines 77-79
    const resultPreserveEnd = exponentialMovingAverage(sampleData, alpha, true);
    assert.strictEqual(resultPreserveEnd[resultPreserveEnd.length - 1].y, 50);
  });

  runTest(
    "savitzkyGolay computes correct values and handles edge cases",
    () => {
      assert.deepStrictEqual(savitzkyGolay([]), []);
      assert.deepStrictEqual(savitzkyGolay(null), null);

      const smallData = [{ x: 1, y: 10 }];
      assert.deepStrictEqual(
        savitzkyGolay(smallData, 5),
        smallData,
        "Returns original data if length < window",
      );

      // Even window size test, it should increment to odd internally
      const evenWindowResult = savitzkyGolay(sampleData, 4, 1, false);
      assert.strictEqual(evenWindowResult.length, 5);

      // Basic calculation check (simplistic given polynomialFit mock-like behavior)
      const result = savitzkyGolay(sampleData, 3, 1, false);
      assert.strictEqual(result.length, 5);
      assert.strictEqual(result[0].y, 10); // Edge point logic
      assert.strictEqual(result[2].y, 30); // Middle point logic

      // Hit lines 123-125
      const resultPreserveEnd = savitzkyGolay(sampleData, 3, 1, true);
      assert.strictEqual(resultPreserveEnd[resultPreserveEnd.length - 1].y, 50);

      // Hit lines 228-229 (polynomial fit where n <= order)
      // If we pass order=10 to savitzkyGolay, it will pass order=10 to polynomialFit
      const highOrderResult = savitzkyGolay(sampleData, 3, 10, false);
      assert.strictEqual(highOrderResult.length, 5);
      // It will just return points[targetIndex]?.y
      assert.strictEqual(highOrderResult[2].y, 30);

      // Hit line 228-229 with out-of-bounds index (should return 0)
      // Pass an order >= window (so n <= order is true) and check if bounds are handled.
      // We also test if order=1 is hit.
      // But actually, savitzkyGolay only calls polynomialFit for indices < halfWindow or > length-1-halfWindow.
      // Let's pass a small array where window is larger.
      const order10Result = savitzkyGolay([{x: 1, y: 10}, {x: 2, y: 20}, {x: 3, y: 30}], 3, 10, false);
      assert.strictEqual(order10Result[0].y, 10);

      // Hit lines 244 (higher orders fallback)
      // When order > 1 but n > order (e.g. window=5, order=3)
      const higherOrderResult = savitzkyGolay(sampleData, 5, 3, false);
      assert.strictEqual(higherOrderResult[0].y, 10); // points[targetIndex]?.y || 0

      // Also pass order > 1 but <= window
      const order2Result = savitzkyGolay(sampleData, 5, 2, false);
      assert.strictEqual(order2Result[0].y, 10);

      // Hit default 0 returns in polynomialFit when data is missing 'y' property
      const dataWithoutY = [{x: 1}, {x: 2}, {x: 3}, {x: 4}, {x: 5}];
      const noYResult1 = savitzkyGolay(dataWithoutY, 5, 5, false);
      assert.strictEqual(noYResult1[0].y, 0); // hits line 228

      const noYResult2 = savitzkyGolay(dataWithoutY, 5, 2, false);
      assert.strictEqual(noYResult2[0].y, 0); // hits line 244
    },
  );

  runTest("lowess computes correct values and handles edge cases", () => {
    assert.deepStrictEqual(lowess([]), []);
    assert.deepStrictEqual(lowess(null), null);

    const smallData = [
      { x: 1, y: 10 },
      { x: 2, y: 20 },
    ];
    assert.deepStrictEqual(
      lowess(smallData, 0.3),
      smallData,
      "Returns original data if length < 3",
    );

    const result = lowess(sampleData, 0.5, false);
    assert.strictEqual(result.length, 5);
    // With such a clean linear progression, lowess should closely approximate original values
    assert.ok(Math.abs(result[2].y - 30) < 5);

    // Hit lines 170-172
    const resultPreserveEnd = lowess(sampleData, 0.5, true);
    assert.strictEqual(resultPreserveEnd[resultPreserveEnd.length - 1].y, 50);

    // Hit line 278 (weightSum === 0 logic) by using bandwidth = 0
    const zeroBandwidthResult = lowess(sampleData, 0, false);
    assert.strictEqual(zeroBandwidthResult[2].y, 30);
  });

  runTest("adaptiveSmoothing handles different volatilities and edge cases", () => {
    assert.deepStrictEqual(adaptiveSmoothing([]), []);
    assert.deepStrictEqual(adaptiveSmoothing(null), null);

    const smallData = [{ x: 1, y: 10 }];
    assert.strictEqual(adaptiveSmoothing(smallData, false).length, 1);

    // low volatility (flat line)
    const lowVol = Array.from({length: 15}, (_, i) => ({x: i, y: 10}));
    const resLow = adaptiveSmoothing(lowVol, false);
    assert.strictEqual(resLow.length, 15);

    // medium volatility (alternating small jumps)
    const medVol = Array.from({length: 15}, (_, i) => ({x: i, y: 10 + (i % 2 === 0 ? 0.3 : 0)}));
    const resMed = adaptiveSmoothing(medVol, false);
    assert.strictEqual(resMed.length, 15);

    // high volatility (large jumps)
    const highVol = Array.from({length: 15}, (_, i) => ({x: i, y: 10 + (i % 2 === 0 ? 5 : 0)}));
    const resHigh = adaptiveSmoothing(highVol, false);
    assert.strictEqual(resHigh.length, 15);
  });

  runTest("smoothFinancialData applies correct configuration", () => {
    // 331-332: null array
    assert.deepStrictEqual(smoothFinancialData(null), null);

    // Basic test to ensure the main export function orchestrates correctly
    const result = smoothFinancialData(sampleData, "balanced", false);

    assert.strictEqual(result.length, 5);
    // First point should be unchanged by EMA
    assert.strictEqual(result[0].y, 10);
    // Should be smoothed, EMA with alpha 0.3
    const expectedSecondY = 0.3 * 20 + 0.7 * 10; // 6 + 7 = 13
    assert.strictEqual(result[1].y, expectedSecondY);

    // Test unknown config string uses fallback "balanced"
    const fallbackResult = smoothFinancialData(sampleData, "not_a_real_config", false);
    assert.strictEqual(fallbackResult.length, 5);

    // Test 'simple' method dispatch
    const simpleResult = smoothFinancialData(
      sampleData,
      {
        method: "simple",
        params: { window: 3 },
        passes: 1,
      },
      false,
    );
    assert.strictEqual(simpleResult.length, 5);

    // Test 'simple' default params
    const simpleResultDef = smoothFinancialData(sampleData, { method: "simple", params: {} }, false);
    assert.strictEqual(simpleResultDef.length, 5);

    // Test 'exponential' method dispatch
    const expResult = smoothFinancialData(sampleData, { method: "exponential", params: { alpha: 0.5 }, passes: "invalid" }, false);
    assert.strictEqual(expResult.length, 5);

    // Test 'exponential' default params
    const expResultDef = smoothFinancialData(sampleData, { method: "exponential", params: {} }, false);
    assert.strictEqual(expResultDef.length, 5);

    // Test 'savitzky' method dispatch
    const savitzkyResult = smoothFinancialData(
      sampleData,
      {
        method: "savitzky",
        params: { window: 5, order: 2 },
        passes: 1,
      },
      false,
    );
    assert.strictEqual(savitzkyResult.length, 5);

    // Test 'savitzky' default params
    const savitzkyResultDef = smoothFinancialData(sampleData, { method: "savitzky", params: {} }, false);
    assert.strictEqual(savitzkyResultDef.length, 5);

    // Test 'lowess' method dispatch
    const lowessResult = smoothFinancialData(
      sampleData,
      {
        method: "lowess",
        params: { bandwidth: 0.3 },
        passes: 1,
      },
      false,
    );
    assert.strictEqual(lowessResult.length, 5);

    // Test 'lowess' default params
    const lowessResultDef = smoothFinancialData(sampleData, { method: "lowess", params: {} }, false);
    assert.strictEqual(lowessResultDef.length, 5);

    // Test 'adaptive' method dispatch
    const adaptiveResult = smoothFinancialData(
      sampleData,
      {
        method: "adaptive",
        params: {},
        passes: 1,
      },
      false,
    );
    assert.strictEqual(adaptiveResult.length, 5);

    // Test default fallback dispatch
    const defaultResult = smoothFinancialData(
      sampleData,
      {
        method: "unknown_method",
        params: {},
        passes: 1,
      },
      false,
    );
    assert.strictEqual(defaultResult.length, 5);
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
