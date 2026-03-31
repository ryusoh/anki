import assert from "assert";
import {
  isTradingDay,
  toIsoDate,
  parseYearFromDate,
  parseQuarterToken,
  resolveQuarterRange,
  normalizeDateOnly,
  getNyDate,
  getTradingDayDate,
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
    // Explicit coverage for NaN date parsing check
    const nanDate = new Date(NaN);
    assert.strictEqual(
      toIsoDate(nanDate),
      "",
      "Should return empty string for NaN date value",
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
    assert.strictEqual(parseYearFromDate({}), null);
    assert.strictEqual(parseYearFromDate(1234), null);
    assert.strictEqual(parseYearFromDate("123"), null);
  });

  runTest("parseQuarterToken parses valid quarters", () => {
    assert.deepStrictEqual(parseQuarterToken("2023q1"), {
      year: 2023,
      quarter: 1,
    });
    assert.deepStrictEqual(parseQuarterToken("2023Q1"), {
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
    assert.strictEqual(parseQuarterToken(1234), null); // non string token
    // Line 68: Number.isFinite(fallbackYear) being false branch for simple token "q1"
    assert.strictEqual(parseQuarterToken("q1", NaN), null);
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

    // Invalid modes fallback to full
    assert.deepStrictEqual(resolveQuarterRange(2023, 1, "invalid_mode"), {
      from: "2023-01-01",
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
    assert.deepStrictEqual(resolveQuarterRange(NaN, 1), {
      from: null,
      to: null,
    });
    assert.deepStrictEqual(resolveQuarterRange(2023, NaN), {
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

    // Juneteenth (Jun 19, 2024 is a Wednesday)
    const juneteenth = new Date("2024-06-19T12:00:00Z");
    assert.strictEqual(isTradingDay(juneteenth), false);

    // MLK Jr. Day (3rd Monday of Jan, Jan 15, 2024)
    const mlkDay = new Date("2024-01-15T12:00:00Z");
    assert.strictEqual(isTradingDay(mlkDay), false);

    // Washington's Birthday (3rd Monday of Feb, Feb 19, 2024)
    const washingtonDay = new Date("2024-02-19T12:00:00Z");
    assert.strictEqual(isTradingDay(washingtonDay), false);

    // Memorial Day (Last Monday of May, May 27, 2024)
    const memorialDay = new Date("2024-05-27T12:00:00Z");
    assert.strictEqual(isTradingDay(memorialDay), false);

    // Labor Day (1st Monday of Sep, Sep 2, 2024)
    const laborDay = new Date("2024-09-02T12:00:00Z");
    assert.strictEqual(isTradingDay(laborDay), false);

    // Thanksgiving Day (4th Thursday of Nov, Nov 28, 2024)
    const thanksgivingDay = new Date("2024-11-28T12:00:00Z");
    assert.strictEqual(isTradingDay(thanksgivingDay), false);
  });

  runTest("getTradingDayDate handles current NY date", () => {
    // Pass a specific deterministic date rather than relying on system time
    const mondayDate = new Date("2023-10-16T12:00:00Z"); // Known trading day
    const sundayDate = new Date("2023-10-15T12:00:00Z"); // Known weekend
    assert.ok(getTradingDayDate(mondayDate) instanceof Date);
    assert.strictEqual(getTradingDayDate(sundayDate), null);

    // Test default param usage
    const res = getTradingDayDate();
    assert.ok(res === null || res instanceof Date);
  });

  runTest("getNyDate returns a valid Date object", () => {
    const d = getNyDate();
    assert.ok(d instanceof Date);
    assert.ok(!Number.isNaN(d.getTime()));
  });

  runTest("parseYearFromDate line 68 coverage", () => {
    const originalParseInt = Number.parseInt;
    try {
      Number.parseInt = () => NaN;
      assert.strictEqual(parseYearFromDate("2023"), null);
    } finally {
      Number.parseInt = originalParseInt;
    }
  });

  // Summary
  console.log("\n" + "=".repeat(60));
  console.log(`\n📊 Results: ${passed} passed, ${failed} failed\n`);

  if (failed > 0) {
    console.log("❌ TESTS FAILED - Date utility has issues\n");
    process.exitCode = 1;
  } else {
    console.log("✅ ALL TESTS PASSED - Date utility working correctly");
  }
}

runTests();
