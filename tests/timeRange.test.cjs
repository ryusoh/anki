/**
 * Time Range Parser Tests
 * Tests parseRange, isValidRange, and formatRange from timeRange.js
 *
 * Run: node tests/timeRange.test.js
 */

const assert = require("assert");

// ============================================================================
// INLINE IMPLEMENTATION (mirrors js/utils/timeRange.js)
// ============================================================================

// We remove the inline implementation and import it from the source file
// to allow c8 to calculate coverage.
// But this file is CommonJS, so we use dynamic import.

// ============================================================================
// TESTS
// ============================================================================

async function runTests() {
  const { parseRange, isValidRange, formatRange } = await import("../js/utils/timeRange.js");
  let passed = 0;
  let failed = 0;

  console.log("🧪 Time Range Parser Tests\n");
  console.log("=".repeat(60));

  // Test 1: Simple month ranges (1m–12m)
  console.log("\n📋 Test 1: Simple month ranges");
  try {
    assert.strictEqual(parseRange("1m"), 30);
    assert.strictEqual(parseRange("2m"), 60);
    assert.strictEqual(parseRange("3m"), 90);
    assert.strictEqual(parseRange("6m"), 180);
    assert.strictEqual(parseRange("12m"), 360);
    console.log("   ✓ 1m=30, 2m=60, 3m=90, 6m=180, 12m=360");
    passed++;
  } catch (e) {
    console.log(`   ✗ ${e.message}`);
    failed++;
  }

  // Test 4b: empty strings
  console.log("\n📋 Test 4b: empty string returns undefined");
  try {
    assert.strictEqual(parseRange("   "), undefined);
    passed++;
  } catch (e) {
    console.log(`   ✗ ${e.message}`);
    failed++;
  }

  // Test 2: Simple year ranges
  console.log("\n📋 Test 2: Simple year ranges");
  try {
    assert.strictEqual(parseRange("1y"), 365);
    assert.strictEqual(parseRange("2y"), 730);
    assert.strictEqual(parseRange("5y"), 1825);
    assert.strictEqual(parseRange("10y"), 3650);
    assert.strictEqual(parseRange("13y"), 4745);
    assert.strictEqual(parseRange("20y"), 7300);
    console.log("   ✓ 1y=365, 2y=730, 5y=1825, 10y=3650, 13y=4745, 20y=7300");
    passed++;
  } catch (e) {
    console.log(`   ✗ ${e.message}`);
    failed++;
  }

  // Test 3: Simple day ranges
  console.log("\n📋 Test 3: Simple day ranges");
  try {
    assert.strictEqual(parseRange("1d"), 1);
    assert.strictEqual(parseRange("7d"), 7);
    assert.strictEqual(parseRange("15d"), 15);
    assert.strictEqual(parseRange("90d"), 90);
    assert.strictEqual(parseRange("365d"), 365);
    console.log("   ✓ 1d=1, 7d=7, 15d=15, 90d=90, 365d=365");
    passed++;
  } catch (e) {
    console.log(`   ✗ ${e.message}`);
    failed++;
  }

  // Test 4: "all" returns null
  console.log("\n📋 Test 4: 'all' returns null");
  try {
    assert.strictEqual(parseRange("all"), null);
    assert.strictEqual(parseRange("ALL"), null);
    assert.strictEqual(parseRange("All"), null);
    console.log("   ✓ 'all', 'ALL', 'All' all return null");
    passed++;
  } catch (e) {
    console.log(`   ✗ ${e.message}`);
    failed++;
  }

  // Test 5: Combo ranges (year + month)
  console.log("\n📋 Test 5: Combo ranges (year + month)");
  try {
    assert.strictEqual(parseRange("1y4m"), 365 + 120);
    assert.strictEqual(parseRange("2y6m"), 730 + 180);
    assert.strictEqual(parseRange("1y1m"), 365 + 30);
    assert.strictEqual(parseRange("3y12m"), 1095 + 360);
    console.log("   ✓ 1y4m=485, 2y6m=910, 1y1m=395, 3y12m=1455");
    passed++;
  } catch (e) {
    console.log(`   ✗ ${e.message}`);
    failed++;
  }

  // Test 6: Combo ranges (month + day)
  console.log("\n📋 Test 6: Combo ranges (month + day)");
  try {
    assert.strictEqual(parseRange("3m9d"), 90 + 9);
    assert.strictEqual(parseRange("1m15d"), 30 + 15);
    assert.strictEqual(parseRange("6m7d"), 180 + 7);
    console.log("   ✓ 3m9d=99, 1m15d=45, 6m7d=187");
    passed++;
  } catch (e) {
    console.log(`   ✗ ${e.message}`);
    failed++;
  }

  // Test 7: Combo ranges (year + month + day)
  console.log("\n📋 Test 7: Combo ranges (year + month + day)");
  try {
    assert.strictEqual(parseRange("2y6m15d"), 730 + 180 + 15);
    assert.strictEqual(parseRange("1y1m1d"), 365 + 30 + 1);
    assert.strictEqual(parseRange("5y3m10d"), 1825 + 90 + 10);
    console.log("   ✓ 2y6m15d=925, 1y1m1d=396, 5y3m10d=1925");
    passed++;
  } catch (e) {
    console.log(`   ✗ ${e.message}`);
    failed++;
  }

  // Test 8: Combo ranges (year + day, no month)
  console.log("\n📋 Test 8: Combo ranges (year + day)");
  try {
    assert.strictEqual(parseRange("1y15d"), 365 + 15);
    assert.strictEqual(parseRange("2y30d"), 730 + 30);
    console.log("   ✓ 1y15d=380, 2y30d=760");
    passed++;
  } catch (e) {
    console.log(`   ✗ ${e.message}`);
    failed++;
  }

  // Test 9: Invalid ranges return undefined
  console.log("\n📋 Test 9: Invalid ranges return undefined");
  try {
    assert.strictEqual(parseRange("13m"), undefined, "13m is invalid (>12)");
    assert.strictEqual(parseRange("0d"), undefined, "0d is invalid");
    assert.strictEqual(parseRange("0m"), undefined, "0m is invalid");
    assert.strictEqual(parseRange("0y"), undefined, "0y is invalid");
    assert.strictEqual(parseRange("abc"), undefined, "abc is invalid");
    assert.strictEqual(parseRange(""), undefined, "empty is invalid");
    assert.strictEqual(parseRange(null), undefined, "null is invalid");
    assert.strictEqual(
      parseRange(undefined),
      undefined,
      "undefined is invalid",
    );
    assert.strictEqual(parseRange("m"), undefined, "bare m is invalid");
    assert.strictEqual(parseRange("y"), undefined, "bare y is invalid");
    assert.strictEqual(parseRange("d"), undefined, "bare d is invalid");
    assert.strictEqual(parseRange("1x"), undefined, "1x is invalid");
    assert.strictEqual(parseRange("-1m"), undefined, "negative is invalid");
    console.log("   ✓ All invalid inputs correctly rejected");
    passed++;
  } catch (e) {
    console.log(`   ✗ ${e.message}`);
    failed++;
  }

  // Test 10: Case insensitivity
  console.log("\n📋 Test 10: Case insensitivity");
  try {
    assert.strictEqual(parseRange("3M"), 90);
    assert.strictEqual(parseRange("2Y"), 730);
    assert.strictEqual(parseRange("15D"), 15);
    assert.strictEqual(parseRange("1Y4M"), 485);
    console.log("   ✓ 3M=90, 2Y=730, 15D=15, 1Y4M=485");
    passed++;
  } catch (e) {
    console.log(`   ✗ ${e.message}`);
    failed++;
  }

  // Test 11: Whitespace handling
  console.log("\n📋 Test 11: Whitespace handling");
  try {
    assert.strictEqual(parseRange("  3m  "), 90);
    assert.strictEqual(parseRange(" all "), null);
    console.log("   ✓ Leading/trailing whitespace trimmed");
    passed++;
  } catch (e) {
    console.log(`   ✗ ${e.message}`);
    failed++;
  }

  // Test 12: isValidRange
  console.log("\n📋 Test 12: isValidRange");
  try {
    assert.strictEqual(isValidRange("3m"), true);
    assert.strictEqual(isValidRange("1y4m"), true);
    assert.strictEqual(isValidRange("all"), true);
    assert.strictEqual(isValidRange("abc"), false);
    assert.strictEqual(isValidRange("13m"), false);
    assert.strictEqual(isValidRange(null), false);
    console.log("   ✓ isValidRange correctly validates all inputs");
    passed++;
  } catch (e) {
    console.log(`   ✗ ${e.message}`);
    failed++;
  }

  // Test 13: formatRange
  console.log("\n📋 Test 13: formatRange");
  try {
    assert.strictEqual(formatRange("3m"), "90 days");
    assert.strictEqual(formatRange("1y"), "365 days");
    assert.strictEqual(formatRange("1y4m"), "485 days");
    assert.strictEqual(formatRange("all"), "all time");
    assert.strictEqual(formatRange("abc"), "unknown");
    console.log("   ✓ formatRange produces correct display strings");
    passed++;
  } catch (e) {
    console.log(`   ✗ ${e.message}`);
    failed++;
  }

  // Test 14: 13m in combo is also invalid
  console.log("\n📋 Test 14: Invalid months in combos");
  try {
    assert.strictEqual(
      parseRange("1y13m"),
      undefined,
      "13m in combo is invalid",
    );
    assert.strictEqual(parseRange("1y0m"), 365, "0m in combo adds 0 months");
    assert.strictEqual(parseRange("1y12m"), 365 + 360, "12m in combo is valid");
    console.log("   ✓ Month validation applies in combos too");
    passed++;
  } catch (e) {
    console.log(`   ✗ ${e.message}`);
    failed++;
  }

  // Test 15: Large year values
  console.log("\n📋 Test 15: Large year values");
  try {
    assert.strictEqual(parseRange("50y"), 50 * 365);
    assert.strictEqual(parseRange("100y"), 100 * 365);
    console.log("   ✓ 50y=18250, 100y=36500");
    passed++;
  } catch (e) {
    console.log(`   ✗ ${e.message}`);
    failed++;
  }

  // Test 18: Additional coverage edge cases (3)
  console.log("\n📋 Test 18: Additional coverage edge cases 3");
  try {
    // line 46: "if (match[1] && years < 1) return undefined;"
    assert.strictEqual(parseRange("0y12m"), undefined);

    // line 49: "return total > 0 ? total : undefined;"
    // We already return undefined for everything < 1, but we can try 0m0d
    // Oh wait, 0m0d returns undefined at line 40: "if (years === 0 && months === 0 && days === 0) return undefined;"
    // Is it possible to reach line 49 with total <= 0 ?
    // years, months, days are all integers >= 0.
    // If they sum to >0, it returns total.
    // If they sum to 0, it means years=0, months=0, days=0, but that's caught at line 40.
    // Wait, what if someone enters negative numbers?
    // The regex /^(?:(\d+)y)?(?:(\d+)m)?(?:(\d+)d)?$/ only matches digits (\d+).
    // Thus years, months, days can only be positive or zero.
    // So total can only be 0 if all are 0.
    // But all being 0 is caught by `if (years === 0 && months === 0 && days === 0) return undefined;`
    // Therefore, the false branch of `total > 0 ? total : undefined` on line 49 is fundamentally mathematically unreachable unless total overflows to negative or NaN, which is practically impossible with standard JS strings parsed from \d+.
    // Let's at least test some boundaries to ensure the line is hit.
    assert.strictEqual(parseRange("1m0d"), 30);
    assert.strictEqual(parseRange("0y1m"), undefined); // 0y gets rejected at line 46

    passed++;
  } catch (e) {
    console.log(`   ✗ ${e.message}`);
    failed++;
  }

  // Summary
  console.log("\n" + "=".repeat(60));
  console.log(`\n📊 Results: ${passed} passed, ${failed} failed\n`);

  if (failed > 0) {
    console.log("❌ TESTS FAILED - Time range parser has issues\n");
    process.exitCode = 1;
  } else {
    console.log("✅ ALL TESTS PASSED - Time range parser working correctly");
  }
}

runTests().catch(console.error);
