/**
 * Calendar Range Filtering Tests for reviews.js
 * Verifies getReviewStatsData() correctly filters by year/quarter tokens,
 * including entries around a deliberate date gap, and that duration/"all"
 * behavior is unchanged.
 *
 * Run: node --experimental-vm-modules --no-warnings tests/reviews_calendar.test.cjs
 */

const test = require("node:test");
const assert = require("assert");

global.window = {};

// Six global entries spanning 2024-12-30 .. 2026-01-01, with a deliberate
// gap at 2025-01-02 (no entry that day) to prove filtering is date-based,
// not index-based.
const GLOBAL_ENTRIES = [
  { date: "2024-12-30", mature: 1, time: 10 },
  { date: "2024-12-31", mature: 2, time: 20 },
  { date: "2025-01-01", mature: 3, time: 30 },
  { date: "2025-01-03", mature: 4, time: 40 },
  { date: "2025-06-30", mature: 5, time: 50 },
  { date: "2026-01-01", mature: 6, time: 60 },
];

const DECK_A_ENTRIES = [
  { date: "2024-12-31", count: 3, time: 30 },
  { date: "2025-01-01", count: 1, time: 10 },
  { date: "2025-06-30", count: 2, time: 20 },
];

function freshMock() {
  global.window.reviewStatsData = {
    reviews: GLOBAL_ENTRIES.map((e) => ({ ...e })),
    reviewsByDeck: { DeckA: DECK_A_ENTRIES.map((e) => ({ ...e })) },
  };
}

const ZERO_SUM = {
  mature: 0,
  young: 0,
  learn: 0,
  relearn: 0,
  time_mature: 0,
  time_young: 0,
  time_learn: 0,
  time_relearn: 0,
  time: 0,
};

test("getReviewStatsData: full-year token filters by date, keeps pre-window sum", async () => {
  freshMock();
  const { getReviewStatsData } = await import("../js/commands/reviews.js");
  const result = getReviewStatsData("2025");
  assert.deepStrictEqual(
    result.map((e) => e.date),
    ["2025-01-01", "2025-01-03", "2025-06-30"],
  );
  assert.deepStrictEqual(result.preSliceSum, {
    ...ZERO_SUM,
    mature: 3,
    time: 30,
  });
});

test("getReviewStatsData: quarter token filters to the quarter only", async () => {
  freshMock();
  const { getReviewStatsData } = await import("../js/commands/reviews.js");
  const result = getReviewStatsData("2025q1");
  assert.deepStrictEqual(
    result.map((e) => e.date),
    ["2025-01-01", "2025-01-03"],
  );
  assert.deepStrictEqual(result.preSliceSum, {
    ...ZERO_SUM,
    mature: 3,
    time: 30,
  });
});

test("getReviewStatsData: future year with no matching entries returns empty slice with full pre-sum", async () => {
  freshMock();
  const { getReviewStatsData } = await import("../js/commands/reviews.js");
  const result = getReviewStatsData("2027");
  assert.strictEqual(result.length, 0);
  assert.deepStrictEqual(result.preSliceSum, {
    ...ZERO_SUM,
    mature: 21,
    time: 210,
  });
});

test("getReviewStatsData: by-deck calendar filter pads window and sums pre-window deck entries", async () => {
  freshMock();
  const { getReviewStatsData } = await import("../js/commands/reviews.js");
  const result = getReviewStatsData("2025", true);
  assert.deepStrictEqual(result.dates, [
    "2025-01-01",
    "2025-01-03",
    "2025-06-30",
  ]);
  assert.deepStrictEqual(result.preSliceSumsByDeck.DeckA, {
    count: 3,
    time: 30,
  });
  const deckAWindow = result.byDeck.DeckA;
  assert.strictEqual(deckAWindow.length, 3);
  assert.strictEqual(deckAWindow[0].date, "2025-01-01");
  assert.strictEqual(deckAWindow[0].count, 1);
  // 2025-01-03 has no DeckA entry -> zero-padded row
  assert.strictEqual(deckAWindow[1].date, "2025-01-03");
  assert.strictEqual(deckAWindow[1].count, 0);
  assert.strictEqual(deckAWindow[2].date, "2025-06-30");
  assert.strictEqual(deckAWindow[2].count, 2);
});

test("getReviewStatsData: duration '1m' and 'all' still return every entry, unchanged", async () => {
  freshMock();
  const { getReviewStatsData } = await import("../js/commands/reviews.js");
  const allDates = GLOBAL_ENTRIES.map((e) => e.date);

  const oneMonth = getReviewStatsData("1m");
  assert.deepStrictEqual(
    oneMonth.map((e) => e.date),
    allDates,
  );
  assert.deepStrictEqual(oneMonth.preSliceSum, ZERO_SUM);

  freshMock();
  const { getReviewStatsData: getReviewStatsData2 } = await import(
    "../js/commands/reviews.js"
  );
  const all = getReviewStatsData2("all");
  assert.deepStrictEqual(
    all.map((e) => e.date),
    allDates,
  );
  assert.deepStrictEqual(all.preSliceSum, ZERO_SUM);
});
