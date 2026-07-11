/**
 * Span/Open-Ended Calendar Range Tests (Phase 2)
 * Tests parseCalendarRange/parseRangeSpec/calendarRangeToDayOffsets for
 * colon syntax: spans (2020:2023), open-from (f:2026, from:2026), and
 * open-to (to:2028) -- ported from the fund's parseSimplifiedDateRange.
 *
 * Run: node --experimental-vm-modules --no-warnings tests/timeRange_span.test.cjs
 */

const test = require("node:test");
const assert = require("assert");

test("parseRangeSpec: year:year span", async () => {
  const { parseRangeSpec } = await import("../js/utils/timeRange.js");
  assert.deepStrictEqual(parseRangeSpec("2027:2028"), {
    kind: "calendar",
    from: "2027-01-01",
    to: "2028-12-31",
    label: "2027 to 2028",
  });
});

test("parseRangeSpec: quarter:quarter span", async () => {
  const { parseRangeSpec } = await import("../js/utils/timeRange.js");
  assert.deepStrictEqual(parseRangeSpec("2023q1:2024q2"), {
    kind: "calendar",
    from: "2023-01-01",
    to: "2024-06-30",
    label: "2023 Q1 to 2024 Q2",
  });
});

test("parseRangeSpec: mixed year/quarter spans", async () => {
  const { parseRangeSpec } = await import("../js/utils/timeRange.js");
  assert.deepStrictEqual(parseRangeSpec("2023:2024q2"), {
    kind: "calendar",
    from: "2023-01-01",
    to: "2024-06-30",
    label: "2023 to 2024 Q2",
  });
  assert.deepStrictEqual(parseRangeSpec("2023q4:2024"), {
    kind: "calendar",
    from: "2023-10-01",
    to: "2024-12-31",
    label: "2023 Q4 to 2024",
  });
});

test("parseRangeSpec: equal-year and mid-year spans are valid", async () => {
  const { parseRangeSpec } = await import("../js/utils/timeRange.js");
  assert.deepStrictEqual(parseRangeSpec("2023:2023"), {
    kind: "calendar",
    from: "2023-01-01",
    to: "2023-12-31",
    label: "2023 to 2023",
  });
  assert.deepStrictEqual(parseRangeSpec("2023:2023q1"), {
    kind: "calendar",
    from: "2023-01-01",
    to: "2023-03-31",
    label: "2023 to 2023 Q1",
  });
});

test("parseRangeSpec: open-from with 'f:' and 'from:' aliases", async () => {
  const { parseRangeSpec } = await import("../js/utils/timeRange.js");
  const expected = {
    kind: "calendar",
    from: "2026-01-01",
    to: null,
    label: "from 2026",
  };
  assert.deepStrictEqual(parseRangeSpec("f:2026"), expected);
  assert.deepStrictEqual(parseRangeSpec("from:2026"), expected);
});

test("parseRangeSpec: open-from with a quarter unit", async () => {
  const { parseRangeSpec } = await import("../js/utils/timeRange.js");
  assert.deepStrictEqual(parseRangeSpec("f:2023q2"), {
    kind: "calendar",
    from: "2023-04-01",
    to: null,
    label: "from 2023 Q2",
  });
});

test("parseRangeSpec: open-to with 'to:'", async () => {
  const { parseRangeSpec } = await import("../js/utils/timeRange.js");
  assert.deepStrictEqual(parseRangeSpec("to:2028"), {
    kind: "calendar",
    from: null,
    to: "2028-12-31",
    label: "to 2028",
  });
  assert.deepStrictEqual(parseRangeSpec("to:2023q2"), {
    kind: "calendar",
    from: null,
    to: "2023-06-30",
    label: "to 2023 Q2",
  });
});

test("parseRangeSpec: colon tokens trim and lowercase like other tokens", async () => {
  const { parseRangeSpec } = await import("../js/utils/timeRange.js");
  assert.deepStrictEqual(parseRangeSpec(" F:2026 "), {
    kind: "calendar",
    from: "2026-01-01",
    to: null,
    label: "from 2026",
  });
  assert.deepStrictEqual(parseRangeSpec("TO:2028"), {
    kind: "calendar",
    from: null,
    to: "2028-12-31",
    label: "to 2028",
  });
});

test("parseRangeSpec: rejects invalid colon tokens", async () => {
  const { parseRangeSpec, isValidRange } = await import(
    "../js/utils/timeRange.js"
  );
  const invalid = [
    "2023:2020",
    "2023q2:2023q1",
    "2023::2024",
    ":2023",
    "2023:",
    "f:",
    "to:",
    "f:3m",
    "to:all",
    "f:2101",
    "t:2026",
    "2020 : 2023",
    "2020:2023:2025",
  ];
  for (const token of invalid) {
    assert.strictEqual(
      parseRangeSpec(token),
      undefined,
      `expected undefined for ${JSON.stringify(token)}`,
    );
    assert.strictEqual(
      isValidRange(token),
      false,
      `expected isValidRange=false for ${JSON.stringify(token)}`,
    );
  }
});

test("formatRange: span/open-ended labels", async () => {
  const { formatRange } = await import("../js/utils/timeRange.js");
  assert.strictEqual(formatRange("2027:2028"), "2027 to 2028");
  assert.strictEqual(formatRange("f:2026"), "from 2026");
  assert.strictEqual(formatRange("to:2028"), "to 2028");
});

test("Phase 1 regression: single-unit shape and duration tokens are unchanged", async () => {
  const { parseCalendarRange, parseRange } = await import(
    "../js/utils/timeRange.js"
  );
  assert.deepStrictEqual(parseCalendarRange("2025"), {
    kind: "calendar",
    from: "2025-01-01",
    to: "2025-12-31",
    label: "2025",
  });
  assert.strictEqual(parseRange("f:2026"), undefined);
});

test("calendarRangeToDayOffsets: open-from in the future clamps end to Infinity", async () => {
  const { parseCalendarRange, calendarRangeToDayOffsets } = await import(
    "../js/utils/timeRange.js"
  );
  const now = new Date(2026, 6, 11); // 2026-07-11 local
  const spec = parseCalendarRange("f:2027");
  assert.deepStrictEqual(calendarRangeToDayOffsets(spec, now), {
    start: 174,
    end: Infinity,
  });
});

test("calendarRangeToDayOffsets: open-from in the past clamps start to 0, end stays unbounded", async () => {
  const { parseCalendarRange, calendarRangeToDayOffsets } = await import(
    "../js/utils/timeRange.js"
  );
  const now = new Date(2026, 6, 11);
  const spec = parseCalendarRange("f:2025");
  assert.deepStrictEqual(calendarRangeToDayOffsets(spec, now), {
    start: 0,
    end: Infinity,
  });
});

test("calendarRangeToDayOffsets: open-to in the future", async () => {
  const { parseCalendarRange, calendarRangeToDayOffsets } = await import(
    "../js/utils/timeRange.js"
  );
  const now = new Date(2026, 6, 11);
  const spec = parseCalendarRange("to:2027");
  assert.deepStrictEqual(calendarRangeToDayOffsets(spec, now), {
    start: 0,
    end: 538,
  });
});

test("calendarRangeToDayOffsets: open-to entirely in the past returns null", async () => {
  const { parseCalendarRange, calendarRangeToDayOffsets } = await import(
    "../js/utils/timeRange.js"
  );
  const now = new Date(2026, 6, 11);
  const spec = parseCalendarRange("to:2025");
  assert.strictEqual(calendarRangeToDayOffsets(spec, now), null);
});

test("RANGE_HELP: mentions calendar spans and keeps YYYY/YYYYqN substrings", async () => {
  const { RANGE_HELP } = await import("../js/utils/timeRange.js");
  assert.ok(RANGE_HELP.includes("YYYY"));
  assert.ok(RANGE_HELP.includes("YYYYqN"));
  assert.ok(RANGE_HELP.includes("f:2026"));
  assert.ok(RANGE_HELP.includes("to:2028"));
});
