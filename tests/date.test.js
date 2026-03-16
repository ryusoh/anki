import assert from "assert";
import {
  isTradingDay,
  toIsoDate,
  parseYearFromDate,
  parseQuarterToken,
  resolveQuarterRange,
  normalizeDateOnly,
} from "../js/utils/date.js";

function runTests() {
  let passed = 0;
  let failed = 0;

  console.log("🧪 Date Utility Tests\n");
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

  runTest("toIsoDate formats correctly", () => {
    assert.strictEqual(
      toIsoDate(new Date(Date.UTC(2023, 0, 15))),
      "2023-01-15",
    );
    assert.strictEqual(
      toIsoDate(new Date(Date.UTC(2023, 11, 31))),
      "2023-12-31",
    );
    assert.strictEqual(
      toIsoDate("invalid"),
      "",
      "Should return empty string for non-dates",
    );
    assert.strictEqual(
      toIsoDate(new Date("invalid date string")),
      "",
      "Should return empty string for invalid dates",
    );
  });

  runTest("parseYearFromDate handles dates and strings", () => {
    assert.strictEqual(
      parseYearFromDate(new Date(Date.UTC(2023, 0, 15))),
      2023,
    );
    assert.strictEqual(parseYearFromDate("2024-05-10"), 2024);
    assert.strictEqual(parseYearFromDate("  2025/01/01"), 2025);
    assert.strictEqual(parseYearFromDate(null), null);
    assert.strictEqual(parseYearFromDate("invalid"), null);
  });

  runTest("parseQuarterToken parses valid quarters", () => {
    assert.deepStrictEqual(parseQuarterToken("2023q1"), {
      year: 2023,
      quarter: 1,
    });
    assert.deepStrictEqual(parseQuarterToken("  2024Q4  "), {
      year: 2024,
      quarter: 4,
    });
    assert.deepStrictEqual(parseQuarterToken("q2", 2023), {
      year: 2023,
      quarter: 2,
    });
    assert.deepStrictEqual(parseQuarterToken("Q3", 2025), {
      year: 2025,
      quarter: 3,
    });
    assert.strictEqual(parseQuarterToken("invalid"), null);
    assert.strictEqual(parseQuarterToken("q5", 2023), null);
    assert.strictEqual(parseQuarterToken(null), null);
  });

  runTest("resolveQuarterRange returns correct date ranges", () => {
    // Q1
    assert.deepStrictEqual(resolveQuarterRange(2023, 1), {
      from: "2023-01-01",
      to: "2023-03-31",
    });
    // Q4
    assert.deepStrictEqual(resolveQuarterRange(2023, 4), {
      from: "2023-10-01",
      to: "2023-12-31",
    });

    // Modes
    assert.deepStrictEqual(resolveQuarterRange(2023, 1, "start"), {
      from: "2023-01-01",
      to: null,
    });
    assert.deepStrictEqual(resolveQuarterRange(2023, 1, "end"), {
      from: null,
      to: "2023-03-31",
    });

    // Invalid inputs
    assert.deepStrictEqual(resolveQuarterRange(null, 1), {
      from: null,
      to: null,
    });
    assert.deepStrictEqual(resolveQuarterRange(2023, null), {
      from: null,
      to: null,
    });
  });

  runTest("normalizeDateOnly strips time", () => {
    const inputDate = new Date("2023-05-15T14:30:00Z");
    const normalized = normalizeDateOnly(inputDate);
    assert.strictEqual(normalized.getHours(), 0);
    assert.strictEqual(normalized.getMinutes(), 0);
    assert.strictEqual(normalized.getSeconds(), 0);
    assert.strictEqual(normalized.getMilliseconds(), 0);

    assert.strictEqual(normalizeDateOnly(null), null);
    assert.strictEqual(normalizeDateOnly("invalid"), null);
  });

  runTest("isTradingDay correctly identifies weekends", () => {
    // Sunday (0)
    const sunday = new Date("2023-10-15T12:00:00Z");
    assert.strictEqual(isTradingDay(sunday), false);

    // Monday (1)
    const monday = new Date("2023-10-16T12:00:00Z");
    assert.strictEqual(isTradingDay(monday), true);

    // Saturday (6)
    const saturday = new Date("2023-10-21T12:00:00Z");
    assert.strictEqual(isTradingDay(saturday), false);
  });

  runTest("isTradingDay correctly identifies major fixed holidays", () => {
    // New Year's Day (Jan 1, 2024 is a Monday)
    const newYear = new Date("2024-01-01T12:00:00Z");
    assert.strictEqual(isTradingDay(newYear), false);

    // Independence Day (Jul 4, 2024 is a Thursday)
    const independenceDay = new Date("2024-07-04T12:00:00Z");
    assert.strictEqual(isTradingDay(independenceDay), false);

    // Christmas Day (Dec 25, 2024 is a Wednesday)
    const christmas = new Date("2024-12-25T12:00:00Z");
    assert.strictEqual(isTradingDay(christmas), false);
  });

  // Summary
  console.log("\n" + "=".repeat(60));
  console.log(`\n📊 Results: ${passed} passed, ${failed} failed\n`);

  if (failed > 0) {
    console.log("❌ TESTS FAILED - Date utility has issues\n");
    process.exit(1);
  } else {
    console.log("✅ ALL TESTS PASSED - Date utility working correctly");
    process.exit(0);
  }
}

runTests();
