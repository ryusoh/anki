/**
 * Calendar Range Filtering Tests for due.js
 * Verifies getFutureDueData() filters day-offsets by a calendar window and
 * renderFutureDueChart() rebases/labels a future-year window correctly.
 * Does not assume a fixed "today" -- expected offsets are computed from the
 * real current date at test runtime, independently of the source's helpers.
 *
 * Run: node --experimental-vm-modules --no-warnings tests/due_calendar.test.cjs
 */

const test = require("node:test");
const assert = require("assert");
const {
  createChartDomMock,
  createMockChartClass,
} = require("./helpers/chartDomMock.cjs");

const { MockChart, getLastConfig } = createMockChartClass();
global.window = { Chart: MockChart };

function makeDomMock() {
  return createChartDomMock();
}
global.document = makeDomMock();

function todayLocal() {
  const n = new Date();
  return new Date(n.getFullYear(), n.getMonth(), n.getDate());
}

function daysBetween(a, b) {
  return Math.round((b - a) / 86400000);
}

function isoDate(d) {
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${mm}-${dd}`;
}

const today = todayLocal();
const currentYear = today.getFullYear();
const nextYear = currentYear + 1;
const lastYear = currentYear - 1;

const currentYearEndOffset = daysBetween(today, new Date(currentYear, 11, 31));
const nextYearStartOffset = daysBetween(today, new Date(nextYear, 0, 1));
const nextYearEndOffset = daysBetween(today, new Date(nextYear, 11, 31));

// Entries covering today through well into next year, with a deliberate
// hole (no entry for day 5) to prove filtering tolerates sparse data.
function buildFutureDue() {
  const entries = [];
  for (let day = 0; day <= nextYearEndOffset; day++) {
    if (day === 5) continue; // sparse hole
    entries.push({ day, mature: day + 1, young: day * 2 });
  }
  return entries;
}

function freshMock() {
  global.window.customStatsData = {
    futureDue: buildFutureDue(),
    futureDueByDeck: {
      DeckA: buildFutureDue().filter((e) => e.day % 3 === 0),
    },
  };
}

test("getFutureDueData: current-year calendar token keeps only this-year offsets", async () => {
  freshMock();
  const { getFutureDueData } = await import("../js/commands/due.js");
  const result = getFutureDueData(String(currentYear));
  const days = result.map((e) => e.day);
  assert.strictEqual(Math.min(...days), 0);
  assert.strictEqual(Math.max(...days), currentYearEndOffset);
  assert.ok(!days.includes(5), "sparse hole must not reappear as an entry");
  assert.ok(
    days.every((d) => d <= currentYearEndOffset),
    "no offset should exceed the end of the current year",
  );
});

test("getFutureDueData: next-year calendar token keeps only next-year offsets (start > 0)", async () => {
  freshMock();
  const { getFutureDueData } = await import("../js/commands/due.js");
  const result = getFutureDueData(String(nextYear));
  const days = result.map((e) => e.day);
  assert.strictEqual(Math.min(...days), nextYearStartOffset);
  assert.strictEqual(Math.max(...days), nextYearEndOffset);
  assert.ok(
    nextYearStartOffset > 0,
    "sanity: next year must start after today",
  );
});

test("getFutureDueData: past-year calendar token returns empty (array and by-deck object)", async () => {
  freshMock();
  const { getFutureDueData } = await import("../js/commands/due.js");
  assert.deepStrictEqual(getFutureDueData(String(lastYear)), []);
  assert.deepStrictEqual(getFutureDueData(String(lastYear), true), {});
});

test("getFutureDueData: by-deck calendar filter mirrors the global filter", async () => {
  freshMock();
  const { getFutureDueData } = await import("../js/commands/due.js");
  const result = getFutureDueData(String(nextYear), true);
  const deckDays = result.DeckA.map((e) => e.day);
  assert.ok(
    deckDays.every((d) => d >= nextYearStartOffset && d <= nextYearEndOffset),
  );
});

test("getFutureDueData: open-from 'f:<next year>' keeps everything from next-year start onward, no upper truncation", async () => {
  freshMock();
  const { getFutureDueData } = await import("../js/commands/due.js");
  const result = getFutureDueData(`f:${nextYear}`);
  const days = result.map((e) => e.day);
  assert.strictEqual(Math.min(...days), nextYearStartOffset);
  // The mock data's own last entry is at nextYearEndOffset -- an
  // unbounded-future window must reach all the way to it, not truncate.
  assert.strictEqual(Math.max(...days), nextYearEndOffset);
});

test("getFutureDueData: open-to 'to:<current year>' keeps offsets 0..end-of-current-year", async () => {
  freshMock();
  const { getFutureDueData } = await import("../js/commands/due.js");
  const result = getFutureDueData(`to:${currentYear}`);
  const days = result.map((e) => e.day);
  assert.strictEqual(Math.min(...days), 0);
  assert.strictEqual(Math.max(...days), currentYearEndOffset);
});

test("getFutureDueData: open-to 'to:<last year>' returns empty (array and by-deck object)", async () => {
  freshMock();
  const { getFutureDueData } = await import("../js/commands/due.js");
  assert.deepStrictEqual(getFutureDueData(`to:${lastYear}`), []);
  assert.deepStrictEqual(getFutureDueData(`to:${lastYear}`, true), {});
});

test("renderFutureDueChart: open-from 'f:<next year>' labels start at next Jan 1 through the last data day", async () => {
  freshMock();
  const { getFutureDueData, renderFutureDueChart } =
    await import("../js/commands/due.js");
  const { parseRangeSpec } = await import("../js/utils/timeRange.js");
  global.document = makeDomMock();

  const spec = parseRangeSpec(`f:${nextYear}`);
  const data = getFutureDueData(`f:${nextYear}`);
  const res = renderFutureDueChart(data, false, undefined, spec);

  assert.strictEqual(res.success, true);
  assert.strictEqual(
    getLastConfig().data.labels[0],
    isoDate(new Date(nextYear, 0, 1)),
  );
  assert.strictEqual(
    getLastConfig().data.labels.length,
    nextYearEndOffset - nextYearStartOffset + 1,
  );
});

test("renderFutureDueChart: next-year window labels start at next Jan 1, not day-0 padding", async () => {
  freshMock();
  const { getFutureDueData, renderFutureDueChart } =
    await import("../js/commands/due.js");
  const { parseRangeSpec } = await import("../js/utils/timeRange.js");
  global.document = makeDomMock();

  const spec = parseRangeSpec(String(nextYear));
  const data = getFutureDueData(String(nextYear));
  const res = renderFutureDueChart(data, false, undefined, spec);

  assert.strictEqual(res.success, true);
  assert.strictEqual(
    getLastConfig().data.labels[0],
    isoDate(new Date(nextYear, 0, 1)),
  );
  assert.strictEqual(
    getLastConfig().data.labels.length,
    nextYearEndOffset - nextYearStartOffset + 1,
  );
});

test("renderFutureDueChart: duration-mode labels are unchanged (Today, Tomorrow, +2d)", async () => {
  freshMock();
  const { renderFutureDueChart } = await import("../js/commands/due.js");
  global.document = makeDomMock();

  const data = [
    { day: 0, mature: 1, young: 1 },
    { day: 1, mature: 1, young: 1 },
    { day: 2, mature: 1, young: 1 },
  ];
  const res = renderFutureDueChart(data, false, null, null);
  assert.strictEqual(res.success, true);
  assert.deepStrictEqual(getLastConfig().data.labels, [
    "Today",
    "Tomorrow",
    "+2d",
  ]);
});
