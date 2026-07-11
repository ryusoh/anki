/**
 * Calendar Range Message Test for retention.js
 * showRetention() reuses getReviewStatsData() (already calendar-aware,
 * see tests/reviews_calendar.test.cjs) -- this pins the message text.
 *
 * Run: node --experimental-vm-modules --no-warnings tests/retention_calendar.test.cjs
 */

const test = require("node:test");
const assert = require("assert");
const {
  createChartDomMock,
  createMockChartClass,
} = require("./helpers/chartDomMock.cjs");

global.window = {
  Chart: createMockChartClass().MockChart,
  reviewStatsData: {
    reviews: [
      { date: "2025-06-01", retention: 0.9 },
      { date: "2025-06-30", retention: 0.85 },
    ],
  },
};

global.document = createChartDomMock();

test("showRetention: calendar year token produces a calendar-style message", async () => {
  const { showRetention } = await import("../js/commands/retention.js");
  assert.strictEqual(
    showRetention("2025"),
    "Rendered retention rate chart (2025).",
  );
});

test("showRetention: quarter token produces a 'YYYY QN' message", async () => {
  const { showRetention } = await import("../js/commands/retention.js");
  assert.strictEqual(
    showRetention("2025q2"),
    "Rendered retention rate chart (2025 Q2).",
  );
});

test("showRetention: duration token message is unchanged", async () => {
  const { showRetention } = await import("../js/commands/retention.js");
  assert.strictEqual(
    showRetention("3m"),
    "Rendered retention rate chart (90 days).",
  );
});
