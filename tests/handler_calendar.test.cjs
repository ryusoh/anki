/**
 * Calendar Range Routing Tests for handler.js
 * End-to-end through handleCommand(): calendar tokens (YYYY, YYYYqN) must
 * route through the same paths as duration tokens, with zero new trie or
 * regex branches (see docs/terminal-calendar-ranges.md §3.2).
 *
 * Run: node --experimental-vm-modules --no-warnings tests/handler_calendar.test.cjs
 */

const test = require("node:test");
const assert = require("assert");

global.gsap = {
  timeline: () => ({
    to: function () {
      return this;
    },
    call: function () {
      return this;
    },
  }),
};

const windowMock = {
  Chart: class {
    constructor() {
      this.data = { datasets: [] };
    }
    destroy() {}
    update() {}
  },
  gsap: global.gsap,
  customStatsData: {
    futureDue: [
      { day: 0, mature: 1, young: 1 },
      { day: 1, mature: 1, young: 1 },
    ],
    futureDueByDeck: {},
  },
  reviewStatsData: {
    reviews: [
      { date: "2024-01-01", mature: 1, young: 1, time: 10 },
      { date: "2025-01-01", mature: 2, young: 1, time: 20 },
    ],
    reviewsByDeck: {},
  },
  innerWidth: 1024,
};
global.window = windowMock;
global.self = windowMock;
global.document = {
  getElementById: (id) => ({
    id,
    classList: { add: () => {}, remove: () => {}, contains: () => false },
    innerHTML: "",
    style: {},
    appendChild: () => {},
    scrollTop: 0,
    scrollHeight: 0,
    getBoundingClientRect: () => ({ top: 0, bottom: 0, height: 100 }),
    clientHeight: 100,
    dataset: {},
    textContent: "",
    replaceChildren: () => {},
    querySelectorAll: () => [],
    getContext: () => ({}),
  }),
  createElement: () => ({
    setAttribute: () => {},
    appendChild: () => {},
    style: {},
    classList: { add: () => {}, remove: () => {}, contains: () => false },
  }),
  createTextNode: (text) => ({ nodeType: 3, textContent: text }),
  querySelector: () => null,
  querySelectorAll: () => [],
};

function captureLines() {
  const lines = [];
  const appendLine = (text, variant) => lines.push({ text, variant });
  return { lines, appendLine };
}

test("handleCommand: 'plot reviews 2025' routes to plot-reviews with the calendar range", async () => {
  const { handleCommand } = await import("../js/commands/handler.js");
  const { lines, appendLine } = captureLines();
  const result = handleCommand("plot reviews 2025", appendLine);
  assert.strictEqual(result.handled, true);
  assert.strictEqual(result.command, "plot-reviews");
  assert.strictEqual(result.range, "2025");
  assert.ok(!lines.some((l) => l.text.includes("Unknown range")));
});

test("handleCommand: 'plot due 2027' routes to plot-due with the calendar range", async () => {
  const { handleCommand } = await import("../js/commands/handler.js");
  const { appendLine } = captureLines();
  const result = handleCommand("plot due 2027", appendLine);
  assert.strictEqual(result.handled, true);
  assert.strictEqual(result.command, "plot-due");
  assert.strictEqual(result.range, "2027");
});

test("handleCommand: 'retention 2024q4' routes to the retention path", async () => {
  const { handleCommand } = await import("../js/commands/handler.js");
  const { appendLine } = captureLines();
  const result = handleCommand("retention 2024q4", appendLine);
  assert.strictEqual(result.handled, true);
  assert.strictEqual(result.command, "retention");
  assert.strictEqual(result.range, "2024q4");
});

test("handleCommand: bare calendar token re-renders the current chart (shortcut path)", async () => {
  const { handleCommand } = await import("../js/commands/handler.js");
  const { appendLine } = captureLines();
  handleCommand("plot reviews", appendLine);
  const result = handleCommand("2023q2", appendLine);
  assert.strictEqual(result.handled, true);
  assert.ok(result.command.startsWith("reviews"));
  assert.strictEqual(result.range, "2023q2");
});

test("handleCommand: out-of-bounds calendar year is an invalid range, not a crash", async () => {
  const { handleCommand } = await import("../js/commands/handler.js");
  const { lines, appendLine } = captureLines();
  const result = handleCommand("plot reviews 2101", appendLine);
  assert.strictEqual(result.handled, true);
  assert.strictEqual(result.error, "invalid range");
  assert.ok(lines.some((l) => l.text.includes("Unknown range: 2101")));
});

test("handleCommand: 'plot reviews 2024:2025' routes to plot-reviews with the span range", async () => {
  const { handleCommand } = await import("../js/commands/handler.js");
  const { lines, appendLine } = captureLines();
  const result = handleCommand("plot reviews 2024:2025", appendLine);
  assert.strictEqual(result.handled, true);
  assert.strictEqual(result.command, "plot-reviews");
  assert.strictEqual(result.range, "2024:2025");
  assert.ok(!lines.some((l) => l.text.includes("Unknown range")));
});

test("handleCommand: bare open-from token re-renders the current chart (shortcut path)", async () => {
  const { handleCommand } = await import("../js/commands/handler.js");
  const { appendLine } = captureLines();
  handleCommand("plot reviews", appendLine);
  const result = handleCommand("f:2026", appendLine);
  assert.strictEqual(result.handled, true);
  assert.ok(result.command.startsWith("reviews"));
  assert.strictEqual(result.range, "f:2026");
});

test("handleCommand: 'plot due to:2028' routes to plot-due with the open-to range", async () => {
  const { handleCommand } = await import("../js/commands/handler.js");
  const { appendLine } = captureLines();
  const result = handleCommand("plot due to:2028", appendLine);
  assert.strictEqual(result.handled, true);
  assert.strictEqual(result.command, "plot-due");
  assert.strictEqual(result.range, "to:2028");
});

test("handleCommand: inverted span is an invalid range, not a crash", async () => {
  const { handleCommand } = await import("../js/commands/handler.js");
  const { lines, appendLine } = captureLines();
  const result = handleCommand("plot reviews 2023:2020", appendLine);
  assert.strictEqual(result.handled, true);
  assert.strictEqual(result.error, "invalid range");
  assert.ok(lines.some((l) => l.text.includes("Unknown range: 2023:2020")));
});

test("RANGE_HELP: exported from handler.js and mentions calendar tokens and spans", async () => {
  const { RANGE_HELP } = await import("../js/commands/handler.js");
  assert.ok(RANGE_HELP.includes("YYYY"));
  assert.ok(RANGE_HELP.includes("YYYYqN"));
  assert.ok(RANGE_HELP.includes("f:2026"));
  assert.ok(RANGE_HELP.includes("to:2028"));
});

test("showHelp and listCharts: mention calendar spans", async () => {
  const { showHelp, listCharts } = await import("../js/commands/handler.js");
  const helpLines = [];
  showHelp((text) => helpLines.push(text));
  assert.ok(helpLines.some((l) => l.includes("f:2026")));

  const chartLines = [];
  listCharts((text) => chartLines.push(text));
  assert.ok(chartLines.some((l) => l.includes("f:2026")));
});

test("handleCommand: invalid-range hint text uses RANGE_HELP, not the old literal", async () => {
  const { handleCommand, RANGE_HELP } = await import(
    "../js/commands/handler.js"
  );
  const { lines, appendLine } = captureLines();
  handleCommand("plot reviews 2101", appendLine);
  assert.ok(lines.some((l) => l.text === RANGE_HELP));
  assert.ok(
    !lines.some((l) => l.text === "Valid ranges: 1m-12m, 1y-Ny, all"),
  );
});
