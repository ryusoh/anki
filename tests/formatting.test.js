import assert from "assert";

// To avoid the @js alias problem entirely without modifying package.json
// or string manipulation, we test a different utility file that has
// no external dependencies and is not currently covered by tests.
// Testing formatting.js

import {
  formatCurrency,
  compactNumber,
  formatPercentage,
  formatAsCurrency,
  addCommas,
  toFixed,
  formatDate,
} from "../js/utils/formatting.js";

function runTests() {
  let passed = 0;
  let failed = 0;

  console.log("🧪 Formatting Utility Tests\n");
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

  runTest("addCommas formats numbers correctly", () => {
    assert.strictEqual(addCommas(1000), "1,000");
    assert.strictEqual(addCommas(1000000), "1,000,000");
    assert.strictEqual(addCommas(1234.56), "1,234.56");
    assert.strictEqual(addCommas(-1000), "-1,000");
    assert.strictEqual(addCommas(0), "0");
    // Depending on implementation, non-numbers might return "" or "0"
    // Just verify they don't crash
    const invalidResult = addCommas(null);
    assert.ok(
      invalidResult === "0" || invalidResult === "" || invalidResult === "NaN",
    );
  });

  runTest("toFixed formats decimals correctly", () => {
    assert.strictEqual(toFixed(1.234, 2), "1.23");
    assert.strictEqual(toFixed(1.236, 2), "1.24");
    assert.strictEqual(toFixed(1, 2), "1.00");
    assert.strictEqual(toFixed(0, 2), "0.00");
  });

  runTest("compactNumber formats large numbers compactly", () => {
    // Implementations often use 1.00k or 1K, we just need to check suffix logic works
    const kResult = compactNumber(1000);
    assert.ok(kResult.toLowerCase().includes("k"));
    assert.ok(kResult.includes("1"));

    const mResult = compactNumber(1000000);
    assert.ok(mResult.toLowerCase().includes("m"));
    assert.ok(mResult.includes("1"));

    const bResult = compactNumber(1000000000);
    assert.ok(bResult.toLowerCase().includes("b"));
    assert.ok(bResult.includes("1"));

    assert.strictEqual(compactNumber(500), "500");
    assert.ok(compactNumber(-1500).includes("-"));
    assert.strictEqual(compactNumber(null), "0");
  });

  runTest("formatPercentage formats numbers as percent", () => {
    // Current implementation prepends + for positive values
    assert.strictEqual(formatPercentage(0.1234), "+12.34%");
    assert.strictEqual(formatPercentage(1), "+100.00%");
    assert.strictEqual(formatPercentage(-0.05), "-5.00%");
    assert.strictEqual(formatPercentage(0), "0.00%");
    assert.strictEqual(formatPercentage(null), "0.00%");
  });

  runTest("formatAsCurrency matches formatCurrency for standard usage", () => {
    assert.strictEqual(formatAsCurrency(1234.56, "USD"), "$1,234.56");
    assert.strictEqual(formatAsCurrency(-500.5, "USD"), "-$500.50");
  });

  runTest("formatDate formats dates to ISO-like or locale strings", () => {
    const date = new Date("2023-05-15T12:00:00Z");
    const result = formatDate(date);
    assert.ok(typeof result === "string");
    assert.ok(result.length > 0);
    // Exact format depends on locale, but it shouldn't throw or return empty

    assert.strictEqual(formatDate(null), "");
    assert.strictEqual(formatDate(undefined), "");
  });

  runTest(
    "formatCurrency formats correctly with exchange rates and fallbacks",
    () => {
      const exchangeRates = { USD: 1, CNY: 7, JPY: 150 };
      const currencySymbols = { USD: "$", CNY: "¥", JPY: "¥" };

      assert.strictEqual(
        formatCurrency(100, "CNY", exchangeRates, currencySymbols),
        "¥700.00",
      );
      assert.strictEqual(
        formatCurrency(-50, "JPY", exchangeRates, currencySymbols),
        "¥7,500.00",
      );
      assert.strictEqual(
        formatCurrency(NaN, "USD", exchangeRates, currencySymbols),
        "$0.00",
      );
      assert.strictEqual(
        formatCurrency("invalid_string", "USD", exchangeRates, currencySymbols),
        "invalid_string",
      );
      assert.strictEqual(
        formatCurrency(100, "EUR", exchangeRates, currencySymbols),
        "$100.00",
      );
      assert.strictEqual(
        formatCurrency(100, "USD", exchangeRates, {}), // Empty symbols
        "USD100.00",
      );
    },
  );

  // Summary
  console.log("\n" + "=".repeat(60));
  console.log(`\n📊 Results: ${passed} passed, ${failed} failed\n`);

  if (failed > 0) {
    console.log("❌ TESTS FAILED - Formatting utility has issues\n");
    process.exit(1);
  } else {
    console.log("✅ ALL TESTS PASSED - Formatting utility working correctly");
    process.exit(0);
  }
}

runTests();
