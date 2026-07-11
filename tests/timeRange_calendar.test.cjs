/**
 * Calendar Range Parser Tests (year/quarter tokens)
 * Tests parseCalendarRange, parseRangeSpec, calendarRangeToDayOffsets,
 * and the widened isValidRange/formatRange from timeRange.js.
 *
 * Run: node --experimental-vm-modules --no-warnings tests/timeRange_calendar.test.cjs
 */

const test = require("node:test");
const assert = require("assert");

test("parseCalendarRange: full year token", async () => {
  const { parseCalendarRange } = await import("../js/utils/timeRange.js");
  assert.deepStrictEqual(parseCalendarRange("2025"), {
    kind: "calendar",
    from: "2025-01-01",
    to: "2025-12-31",
    label: "2025",
  });
});

test("parseCalendarRange: quarter token, case-insensitive and trimmed", async () => {
  const { parseCalendarRange } = await import("../js/utils/timeRange.js");
  const expected = {
    kind: "calendar",
    from: "2023-04-01",
    to: "2023-06-30",
    label: "2023 Q2",
  };
  assert.deepStrictEqual(parseCalendarRange("2023q2"), expected);
  assert.deepStrictEqual(parseCalendarRange("2023Q2"), expected);
  assert.deepStrictEqual(parseCalendarRange(" 2023q2 "), expected);
});

test("parseCalendarRange: all four quarter boundaries", async () => {
  const { parseCalendarRange } = await import("../js/utils/timeRange.js");
  assert.deepStrictEqual(parseCalendarRange("2024q1"), {
    kind: "calendar",
    from: "2024-01-01",
    to: "2024-03-31",
    label: "2024 Q1",
  });
  assert.deepStrictEqual(parseCalendarRange("2024q2"), {
    kind: "calendar",
    from: "2024-04-01",
    to: "2024-06-30",
    label: "2024 Q2",
  });
  assert.deepStrictEqual(parseCalendarRange("2024q3"), {
    kind: "calendar",
    from: "2024-07-01",
    to: "2024-09-30",
    label: "2024 Q3",
  });
  assert.deepStrictEqual(parseCalendarRange("2024q4"), {
    kind: "calendar",
    from: "2024-10-01",
    to: "2024-12-31",
    label: "2024 Q4",
  });
});

test("parseCalendarRange: leap year Q1 still ends 03-31 (Feb is not a quarter boundary)", async () => {
  const { parseCalendarRange } = await import("../js/utils/timeRange.js");
  assert.strictEqual(parseCalendarRange("2024q1").to, "2024-03-31");
});

test("parseCalendarRange: rejects invalid calendar tokens", async () => {
  const { parseCalendarRange } = await import("../js/utils/timeRange.js");
  const invalid = [
    "2023q5",
    "2023q0",
    "202",
    "20255",
    "1969",
    "2100",
    "q2",
    "2023 q2",
    "",
    null,
    undefined,
  ];
  for (const token of invalid) {
    assert.strictEqual(
      parseCalendarRange(token),
      undefined,
      `expected undefined for ${JSON.stringify(token)}`,
    );
  }
});

test("parseCalendarRange: accepts year bounds 1970 and 2099", async () => {
  const { parseCalendarRange } = await import("../js/utils/timeRange.js");
  assert.strictEqual(parseCalendarRange("1970").kind, "calendar");
  assert.strictEqual(parseCalendarRange("2099").kind, "calendar");
});

test("parseRangeSpec: routes calendar tokens to calendar spec", async () => {
  const { parseRangeSpec } = await import("../js/utils/timeRange.js");
  assert.deepStrictEqual(parseRangeSpec("2025"), {
    kind: "calendar",
    from: "2025-01-01",
    to: "2025-12-31",
    label: "2025",
  });
});

test("parseRangeSpec: routes duration tokens to duration spec", async () => {
  const { parseRangeSpec } = await import("../js/utils/timeRange.js");
  assert.deepStrictEqual(parseRangeSpec("3m"), { kind: "duration", days: 90 });
  assert.deepStrictEqual(parseRangeSpec("1y4m"), {
    kind: "duration",
    days: 485,
  });
});

test("parseRangeSpec: routes 'all' to all spec", async () => {
  const { parseRangeSpec } = await import("../js/utils/timeRange.js");
  assert.deepStrictEqual(parseRangeSpec("all"), { kind: "all" });
});

test("parseRangeSpec: invalid token returns undefined", async () => {
  const { parseRangeSpec } = await import("../js/utils/timeRange.js");
  assert.strictEqual(parseRangeSpec("abc"), undefined);
  assert.strictEqual(parseRangeSpec("2023q5"), undefined);
  assert.strictEqual(parseRangeSpec("2101"), undefined);
});

test("parseRange: unchanged, does not accept calendar tokens (no grammar collision)", async () => {
  const { parseRange } = await import("../js/utils/timeRange.js");
  assert.strictEqual(parseRange("2025"), undefined);
  assert.strictEqual(parseRange("2023q2"), undefined);
});

test("isValidRange: accepts calendar tokens", async () => {
  const { isValidRange } = await import("../js/utils/timeRange.js");
  assert.strictEqual(isValidRange("2025"), true);
  assert.strictEqual(isValidRange("2023q2"), true);
  assert.strictEqual(isValidRange("2023q5"), false);
  assert.strictEqual(isValidRange("2101"), false);
});

test("isValidRange: duration/all behavior unchanged", async () => {
  const { isValidRange } = await import("../js/utils/timeRange.js");
  assert.strictEqual(isValidRange("3m"), true);
  assert.strictEqual(isValidRange("1y4m"), true);
  assert.strictEqual(isValidRange("all"), true);
  assert.strictEqual(isValidRange("abc"), false);
  assert.strictEqual(isValidRange("13m"), false);
  assert.strictEqual(isValidRange(null), false);
});

test("formatRange: calendar tokens produce human labels", async () => {
  const { formatRange } = await import("../js/utils/timeRange.js");
  assert.strictEqual(formatRange("2025"), "2025");
  assert.strictEqual(formatRange("2023q2"), "2023 Q2");
});

test("formatRange: duration/all/unknown behavior unchanged", async () => {
  const { formatRange } = await import("../js/utils/timeRange.js");
  assert.strictEqual(formatRange("3m"), "90 days");
  assert.strictEqual(formatRange("1y"), "365 days");
  assert.strictEqual(formatRange("all"), "all time");
  assert.strictEqual(formatRange("abc"), "unknown");
});

test("calendarRangeToDayOffsets: window fully in the future is clamped to start today", async () => {
  const { parseCalendarRange, calendarRangeToDayOffsets } = await import(
    "../js/utils/timeRange.js"
  );
  const now = new Date(2026, 6, 11); // 2026-07-11 local
  const spec2026 = parseCalendarRange("2026");
  assert.deepStrictEqual(calendarRangeToDayOffsets(spec2026, now), {
    start: 0,
    end: 173,
  });
});

test("calendarRangeToDayOffsets: window entirely next year", async () => {
  const { parseCalendarRange, calendarRangeToDayOffsets } = await import(
    "../js/utils/timeRange.js"
  );
  const now = new Date(2026, 6, 11);
  const spec2027 = parseCalendarRange("2027");
  assert.deepStrictEqual(calendarRangeToDayOffsets(spec2027, now), {
    start: 174,
    end: 538,
  });
});

test("calendarRangeToDayOffsets: window entirely in the past returns null", async () => {
  const { parseCalendarRange, calendarRangeToDayOffsets } = await import(
    "../js/utils/timeRange.js"
  );
  const now = new Date(2026, 6, 11);
  const spec2025 = parseCalendarRange("2025");
  assert.strictEqual(calendarRangeToDayOffsets(spec2025, now), null);
});

test("calendarRangeToDayOffsets: quarter spanning today", async () => {
  const { parseCalendarRange, calendarRangeToDayOffsets } = await import(
    "../js/utils/timeRange.js"
  );
  const now = new Date(2026, 6, 11);
  const spec = parseCalendarRange("2026q3"); // 2026-07-01..2026-09-30
  assert.deepStrictEqual(calendarRangeToDayOffsets(spec, now), {
    start: 0,
    end: 81,
  });
});
