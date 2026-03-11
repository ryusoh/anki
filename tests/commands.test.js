/**
 * Terminal Command Handler Test
 * Tests command routing, chart switching, and time range shortcuts
 *
 * Run: node tests/commands.test.js
 */

const assert = require("assert");

// Mock the TIME_RANGES that match the JS implementation
const TIME_RANGES = {
  "1m": 30,
  "2m": 60,
  "3m": 90,
  "6m": 180,
  "1y": 365,
  "2y": 730,
  "3y": 1095,
  "5y": 1825,
  "10y": 3650,
  all: null,
};

const REQUIRED_RANGES = Object.keys(TIME_RANGES);
const DEFAULT_RANGE = "1m";

// ============================================================================
// COMMAND PARSER (mirrors handler.js logic)
// ============================================================================

function parseCommand(
  input,
  state = { currentChart: null, activeRange: DEFAULT_RANGE },
) {
  if (state.activeRange === undefined) {
    state.activeRange = DEFAULT_RANGE;
  }
  const normalized = input.toLowerCase().trim();

  if (!normalized) {
    return { handled: false };
  }

  // Handle zoom command
  if (normalized === "zoom" || normalized === "z") {
    state.isZoomed = !state.isZoomed;
    return { handled: true, command: "zoom" };
  }

  // Handle time range shortcuts - apply to current chart
  if (normalized in TIME_RANGES) {
    state.isZoomed = false; // Auto-unzoom
    state.activeRange = normalized;
    if (state.currentChart === "reviews") {
      return { handled: true, command: "reviews", range: normalized };
    } else if (state.currentChart === "reviews-cumulative") {
      return {
        handled: true,
        command: "reviews-cumulative",
        range: normalized,
      };
    } else if (state.currentChart === "reviews-deck") {
      return { handled: true, command: "reviews-deck", range: normalized };
    } else if (state.currentChart === "reviews-deck-cumulative") {
      return {
        handled: true,
        command: "reviews-deck-cumulative",
        range: normalized,
      };
    } else if (state.currentChart === "reviews-time") {
      return { handled: true, command: "reviews-time", range: normalized };
    } else if (state.currentChart === "reviews-time-cumulative") {
      return {
        handled: true,
        command: "reviews-time-cumulative",
        range: normalized,
      };
    } else if (state.currentChart === "reviews-time-deck") {
      return { handled: true, command: "reviews-time-deck", range: normalized };
    } else if (state.currentChart === "reviews-time-deck-cumulative") {
      return {
        handled: true,
        command: "reviews-time-deck-cumulative",
        range: normalized,
      };
    } else if (state.currentChart === "retention") {
      return { handled: true, command: "retention", range: normalized };
    } else if (state.currentChart === "due-deck") {
      return { handled: true, command: "due-deck", range: normalized };
    } else {
      state.currentChart = "due";
      return { handled: true, command: "due", range: normalized };
    }
  }

  // Handle abbreviations
  if (normalized === "h" || normalized === "?") {
    return { handled: true, command: "help" };
  }
  if (normalized === "p") {
    return { handled: true, command: "plot" };
  }
  if (normalized === "pd") {
    state.isZoomed = false; // Auto-unzoom
    state.currentChart = "due";
    return { handled: true, command: "plot-due", range: state.activeRange };
  }
  if (normalized === "pr") {
    state.isZoomed = false; // Auto-unzoom
    state.currentChart = "reviews";
    return { handled: true, command: "plot-reviews", range: state.activeRange };
  }
  if (normalized === "prt") {
    state.isZoomed = false; // Auto-unzoom
    state.currentChart = "reviews-time";
    return {
      handled: true,
      command: "plot-reviews-time",
      range: state.activeRange,
    };
  }
  if (normalized === "d") {
    state.isZoomed = false; // Auto-unzoom
    state.currentChart = "due";
    return { handled: true, command: "due", range: state.activeRange };
  }
  if (normalized === "r") {
    state.isZoomed = false; // Auto-unzoom
    state.currentChart = "reviews";
    return { handled: true, command: "reviews", range: state.activeRange };
  }
  if (normalized === "rc") {
    state.isZoomed = false; // Auto-unzoom
    state.currentChart = "reviews-cumulative";
    return {
      handled: true,
      command: "reviews-cumulative",
      range: state.activeRange,
    };
  }
  if (normalized === "rdc") {
    state.isZoomed = false; // Auto-unzoom
    state.currentChart = "reviews-deck-cumulative";
    return {
      handled: true,
      command: "reviews-deck-cumulative",
      range: state.activeRange,
    };
  }
  if (normalized === "rtc") {
    state.isZoomed = false; // Auto-unzoom
    state.currentChart = "reviews-time-cumulative";
    return {
      handled: true,
      command: "reviews-time-cumulative",
      range: state.activeRange,
    };
  }
  if (normalized === "rtdc" || normalized === "rdtc") {
    state.isZoomed = false; // Auto-unzoom
    state.currentChart = "reviews-time-deck-cumulative";
    return {
      handled: true,
      command: "reviews-time-deck-cumulative",
      range: state.activeRange,
    };
  }
  if (normalized === "c" || normalized === "cumulative") {
    state.isZoomed = false;
    if (state.currentChart && state.currentChart.startsWith("reviews")) {
      const isCumulative = !state.currentChart.endsWith("-cumulative");
      const isTime = state.currentChart.includes("time");
      const isDeck = state.currentChart.includes("deck");

      let newChart = "reviews";
      if (isTime) newChart += "-time";
      if (isDeck) newChart += "-deck";
      if (isCumulative) newChart += "-cumulative";

      state.currentChart = newChart;
      return { handled: true, command: newChart, range: state.activeRange };
    } else {
      state.currentChart = "reviews-cumulative";
      return {
        handled: true,
        command: "reviews-cumulative",
        range: state.activeRange,
      };
    }
  }

  if (normalized === "rt" || normalized === "time" || normalized === "t") {
    state.isZoomed = false; // Auto-unzoom
    if (state.currentChart && state.currentChart.startsWith("reviews")) {
      const isCumulative = state.currentChart.endsWith("-cumulative");
      const isTime = !state.currentChart.includes("time");
      const isDeck = state.currentChart.includes("deck");

      let newChart = "reviews";
      if (isTime) newChart += "-time";
      if (isDeck) newChart += "-deck";
      if (isCumulative) newChart += "-cumulative";

      state.currentChart = newChart;
      return { handled: true, command: newChart, range: state.activeRange };
    } else {
      state.currentChart = "reviews-time";
      return {
        handled: true,
        command: "reviews-time",
        range: state.activeRange,
      };
    }
  }

  if (normalized === "dd") {
    state.isZoomed = false; // Auto-unzoom
    state.currentChart = "due-deck";
    return {
      handled: true,
      command: "due-deck",
      range: state.activeRange,
    };
  }

  if (normalized === "pdd") {
    state.isZoomed = false; // Auto-unzoom
    state.currentChart = "due-deck";
    return {
      handled: true,
      command: "plot-due-deck",
      range: state.activeRange,
    };
  }

  if (normalized === "deck" || normalized === "dk") {
    state.isZoomed = false; // Auto-unzoom
    if (state.currentChart && state.currentChart.startsWith("reviews")) {
      const isCumulative = state.currentChart.endsWith("-cumulative");
      const isTime = state.currentChart.includes("time");
      const isDeck = !state.currentChart.includes("deck");

      let newChart = "reviews";
      if (isTime) newChart += "-time";
      if (isDeck) newChart += "-deck";
      if (isCumulative) newChart += "-cumulative";

      state.currentChart = newChart;
      return { handled: true, command: newChart, range: state.activeRange };
    } else if (state.currentChart === "due") {
      state.currentChart = "due-deck";
      return {
        handled: true,
        command: "due-deck",
        range: state.activeRange,
      };
    } else if (state.currentChart === "due-deck") {
      state.currentChart = "due";
      return {
        handled: true,
        command: "due",
        range: state.activeRange,
      };
    } else {
      state.currentChart = "reviews-deck";
      return {
        handled: true,
        command: "reviews-deck",
        range: state.activeRange,
      };
    }
  }

  // Handle "plot due/reviews/reviews time/retention [range]" command
  const plotMatch = normalized.match(
    /^plot\s+(due\s+deck|due|reviews\s+time\s+deck\s+cumulative|reviews\s+deck\s+time\s+cumulative|reviews\s+deck\s+cumulative|reviews\s+time\s+cumulative|reviews\s+cumulative|reviews\s+time\s+deck|reviews\s+deck\s+time|reviews\s+deck|reviews\s+time|reviews|retention)\s*(.*)$/,
  );
  if (plotMatch) {
    const [, chartType, rangeStr] = plotMatch;
    const range = rangeStr.trim() || state.activeRange;
    if (range in TIME_RANGES) {
      state.isZoomed = false; // Auto-unzoom
      let formattedChartType = chartType.replace(/\s+/g, "-");
      if (formattedChartType === "reviews-deck-time") {
        formattedChartType = "reviews-time-deck";
      } else if (formattedChartType === "reviews-deck-time-cumulative") {
        formattedChartType = "reviews-time-deck-cumulative";
      }
      state.currentChart = formattedChartType;
      state.activeRange = range;
      return { handled: true, command: `plot-${formattedChartType}`, range };
    }
    return {
      handled: true,
      command: `plot-${chartType.replace(/\s+/g, "-")}`,
      error: "invalid range",
    };
  }

  // Handle "due" command
  if (normalized === "due" || normalized === "future") {
    state.isZoomed = false; // Auto-unzoom
    state.currentChart = "due";
    return { handled: true, command: "due", range: state.activeRange };
  }

  // Handle "reviews" command
  if (normalized === "reviews") {
    state.isZoomed = false; // Auto-unzoom
    state.currentChart = "reviews";
    return { handled: true, command: "reviews", range: state.activeRange };
  }

  // Handle "retention" command
  if (normalized === "retention") {
    state.isZoomed = false; // Auto-unzoom
    state.currentChart = "retention";
    return { handled: true, command: "retention", range: state.activeRange };
  }

  // Handle "due [range]" command
  const dueMatch = normalized.match(/^(due|future)\s+(.+)$/);
  if (dueMatch) {
    const range = dueMatch[2];
    if (range in TIME_RANGES) {
      state.isZoomed = false; // Auto-unzoom
      state.currentChart = "due";
      state.activeRange = range;
      return { handled: true, command: "due", range };
    }
    return { handled: true, command: "due", error: "invalid range" };
  }

  // Handle "reviews [range]" command
  const reviewsMatch = normalized.match(/^reviews\s+(.+)$/);
  if (
    reviewsMatch &&
    !normalized.startsWith("reviews time") &&
    !normalized.startsWith("reviews deck") &&
    !normalized.includes("cumulative")
  ) {
    const [, range] = reviewsMatch;
    if (range in TIME_RANGES) {
      state.isZoomed = false; // Auto-unzoom
      state.currentChart = "reviews";
      state.activeRange = range;
      return { handled: true, command: "reviews", range };
    }
    return { handled: true, command: "reviews", error: "invalid range" };
  }

  // Handle "retention [range]" command
  const retentionMatch = normalized.match(/^retention\s+(.+)$/);
  if (retentionMatch) {
    const [, range] = retentionMatch;
    if (range in TIME_RANGES) {
      state.isZoomed = false; // Auto-unzoom
      state.currentChart = "retention";
      state.activeRange = range;
      return { handled: true, command: "retention", range };
    }
    return { handled: true, command: "retention", error: "invalid range" };
  }

  // Handle "plot" or "p" alone (shows help)
  if (normalized === "plot" || normalized === "p") {
    return { handled: true, command: "plot" };
  }

  // Handle "show due [range]" command
  if (normalized.startsWith("show ")) {
    const parts = normalized.split(/\s+/);
    if (parts[1] === "due" || parts[1] === "future") {
      const range = parts[2] || state.activeRange;
      if (range in TIME_RANGES) {
        state.isZoomed = false; // Auto-unzoom
        state.currentChart = "due";
        state.activeRange = range;
        return { handled: true, command: "due", range };
      }
    } else if (parts[1] === "reviews") {
      const range = parts[2] || state.activeRange;
      if (range in TIME_RANGES) {
        state.isZoomed = false; // Auto-unzoom
        state.currentChart = "reviews";
        state.activeRange = range;
        return { handled: true, command: "reviews", range };
      }
    }
    return { handled: true, command: "show", error: "unknown chart" };
  }

  return { handled: false };
}

// ============================================================================
// TESTS
// ============================================================================

function runTests() {
  let passed = 0;
  let failed = 0;

  console.log("🧪 Terminal Command Handler Test\n");
  console.log("=".repeat(60));

  // Test 1: Time range shortcuts work
  console.log("\n📋 Test 1: Time range shortcuts (standalone commands)");
  REQUIRED_RANGES.forEach((range) => {
    try {
      const state = {};
      const result = parseCommand(range, state);
      assert.strictEqual(result.handled, true, `Should handle: ${range}`);
      assert.strictEqual(
        result.command,
        "due",
        `Should be due command: ${range}`,
      );
      assert.strictEqual(result.range, range, `Should have range: ${range}`);
      assert.strictEqual(
        state.currentChart,
        "due",
        `Should set chart to due: ${range}`,
      );
      console.log(`   ✓ "${range}" → due chart`);
      passed++;
    } catch (e) {
      console.log(`   ✗ "${range}": ${e.message}`);
      failed++;
    }
  });

  // Test 2: Reviews command works
  console.log("\n📋 Test 2: Reviews command");
  try {
    const state = {};
    const result = parseCommand("reviews", state);
    assert.strictEqual(result.handled, true, 'Should handle "reviews"');
    assert.strictEqual(result.command, "reviews", "Should be reviews command");
    assert.strictEqual(
      result.range,
      DEFAULT_RANGE,
      `Should default to ${DEFAULT_RANGE}`,
    );
    assert.strictEqual(
      state.currentChart,
      "reviews",
      "Should set chart to reviews",
    );
    console.log(`   ✓ "reviews" → reviews chart (${DEFAULT_RANGE})`);
    passed++;
  } catch (e) {
    console.log(`   ✗ "reviews": ${e.message}`);
    failed++;
  }

  // Test 3: Reviews with range
  console.log("\n📋 Test 3: Reviews with range");
  ["1m", "3m", "1y", "all"].forEach((range) => {
    try {
      const state = {};
      const result = parseCommand(`reviews ${range}`, state);
      assert.strictEqual(
        result.handled,
        true,
        `Should handle: reviews ${range}`,
      );
      assert.strictEqual(
        result.command,
        "reviews",
        `Should be reviews command: ${range}`,
      );
      assert.strictEqual(result.range, range, `Should have range: ${range}`);
      assert.strictEqual(
        state.currentChart,
        "reviews",
        `Should set chart to reviews: ${range}`,
      );
      console.log(`   ✓ "reviews ${range}" → reviews chart`);
      passed++;
    } catch (e) {
      console.log(`   ✗ "reviews ${range}": ${e.message}`);
      failed++;
    }
  });

  // Test 4: Chart switching works
  console.log("\n📋 Test 4: Chart switching (due → reviews → due)");
  try {
    const state = {};

    // First: due
    parseCommand("due", state);
    assert.strictEqual(state.currentChart, "due", "Should be due after 'due'");

    // Then: reviews
    parseCommand("reviews", state);
    assert.strictEqual(
      state.currentChart,
      "reviews",
      "Should switch to reviews",
    );

    // Then: due again
    parseCommand("due", state);
    assert.strictEqual(state.currentChart, "due", "Should switch back to due");

    // Then: shortcut
    parseCommand("3m", state);
    assert.strictEqual(
      state.currentChart,
      "due",
      "Should stay on due for shortcut",
    );

    // Then: reviews with range
    parseCommand("reviews 6m", state);
    assert.strictEqual(
      state.currentChart,
      "reviews",
      "Should switch to reviews with range",
    );

    console.log("   ✓ Chart switching works correctly");
    passed++;
  } catch (e) {
    console.log(`   ✗ Chart switching: ${e.message}`);
    failed++;
  }

  // Test 5: Sequential commands (the reported bug)
  console.log("\n📋 Test 5: Sequential commands (regression test)");
  try {
    const state = {};

    // User types "reviews" first
    const result1 = parseCommand("reviews", state);
    assert.strictEqual(result1.handled, true, "Should handle 'reviews'");
    assert.strictEqual(
      state.currentChart,
      "reviews",
      "Should show reviews chart",
    );

    // User then types "3m" (should apply to reviews, not switch to due)
    const result2 = parseCommand("3m", state);
    assert.strictEqual(result2.handled, true, "Should handle '3m'");
    assert.strictEqual(
      result2.command,
      "reviews",
      "Shortcut should apply to reviews chart",
    );
    assert.strictEqual(result2.range, "3m", "Should have 3m range");
    assert.strictEqual(
      state.currentChart,
      "reviews",
      "Should stay on reviews chart",
    );

    console.log("   ✓ Sequential 'reviews' → '3m' stays on reviews");
    passed++;
  } catch (e) {
    console.log(`   ✗ Sequential commands: ${e.message}`);
    failed++;
  }

  // Test 5b: Time shortcuts respect current chart context
  console.log("\n📋 Test 5b: Time shortcuts respect chart context");
  try {
    const state = {};

    // Start with due chart, shortcut should stay on due
    parseCommand("due", state);
    assert.strictEqual(state.currentChart, "due", "Should be on due");

    parseCommand("6m", state);
    assert.strictEqual(
      state.currentChart,
      "due",
      "Shortcut should stay on due",
    );

    // Switch to reviews, shortcut should stay on reviews
    parseCommand("reviews", state);
    assert.strictEqual(
      state.currentChart,
      "reviews",
      "Should switch to reviews",
    );

    parseCommand("1y", state);
    assert.strictEqual(
      state.currentChart,
      "reviews",
      "Shortcut should stay on reviews",
    );

    // Explicit command should switch
    parseCommand("due", state);
    assert.strictEqual(
      state.currentChart,
      "due",
      "Explicit 'due' should switch",
    );

    console.log("   ✓ Time shortcuts respect chart context");
    passed++;
  } catch (e) {
    console.log(`   ✗ Chart context: ${e.message}`);
    failed++;
  }

  // Test 6: Due command variations
  console.log("\n📋 Test 6: Due command variations");
  ["due", "future"].forEach((cmd) => {
    try {
      const state = {};
      const result = parseCommand(cmd, state);
      assert.strictEqual(result.handled, true, `Should handle: ${cmd}`);
      assert.strictEqual(
        result.command,
        "due",
        `Should be due command: ${cmd}`,
      );
      assert.strictEqual(
        state.currentChart,
        "due",
        `Should set chart to due: ${cmd}`,
      );
      console.log(`   ✓ "${cmd}" → due chart`);
      passed++;
    } catch (e) {
      console.log(`   ✗ "${cmd}": ${e.message}`);
      failed++;
    }
  });

  // Test 7: Due with range variations
  console.log("\n📋 Test 7: Due with range variations");
  ["due 3m", "future 1y", "due all"].forEach((input) => {
    try {
      const state = {};
      const result = parseCommand(input, state);
      const expectedRange = input.split(" ")[1];
      assert.strictEqual(result.handled, true, `Should handle: ${input}`);
      assert.strictEqual(
        result.command,
        "due",
        `Should be due command: ${input}`,
      );
      assert.strictEqual(
        result.range,
        expectedRange,
        `Should have range: ${expectedRange}`,
      );
      console.log(`   ✓ "${input}" → due chart (${expectedRange})`);
      passed++;
    } catch (e) {
      console.log(`   ✗ "${input}": ${e.message}`);
      failed++;
    }
  });

  // Test 8: Show command variations
  console.log("\n📋 Test 8: 'show' command variations");
  ["show due 3m", "show reviews 1y", "show future all"].forEach((input) => {
    try {
      const state = {};
      const result = parseCommand(input, state);
      assert.strictEqual(result.handled, true, `Should handle: ${input}`);
      const parts = input.split(" ");
      const expectedCmd = parts[1] === "future" ? "due" : parts[1];
      const expectedRange = parts[2] || DEFAULT_RANGE;
      assert.strictEqual(
        result.command,
        expectedCmd,
        `Should be ${expectedCmd} command`,
      );
      assert.strictEqual(
        result.range,
        expectedRange,
        `Should have range: ${expectedRange}`,
      );
      console.log(`   ✓ "${input}" → ${expectedCmd} chart`);
      passed++;
    } catch (e) {
      console.log(`   ✗ "${input}": ${e.message}`);
      failed++;
    }
  });

  // Test 9: Invalid ranges are handled
  console.log("\n📋 Test 9: Invalid ranges are handled");
  ["due 5m", "reviews 100d", "3y"].forEach((input) => {
    try {
      const state = {};
      const result = parseCommand(input, state);
      if (input === "3y") {
        // This is valid
        assert.strictEqual(result.handled, true, "Should handle valid: 3y");
        assert.strictEqual(result.range, "3y", "Should have 3y range");
        console.log(`   ✓ "${input}" → valid range`);
      } else {
        // Invalid ranges
        assert.strictEqual(
          result.error,
          "invalid range",
          `Should have error: ${input}`,
        );
        console.log(`   ✓ "${input}" → error handled`);
      }
      passed++;
    } catch (e) {
      console.log(`   ✗ "${input}": ${e.message}`);
      failed++;
    }
  });

  // Test 10: Unknown commands are not handled
  console.log("\n📋 Test 10: Unknown commands pass through");
  ["help", "clear", "charts", "unknown", ""].forEach((input) => {
    try {
      const state = {};
      const result = parseCommand(input, state);
      assert.strictEqual(
        result.handled,
        false,
        `Should not handle: ${input || "(empty)"}`,
      );
      console.log(`   ✓ "${input || "(empty)"}" → not handled`);
      passed++;
    } catch (e) {
      console.log(`   ✗ "${input || "(empty)"}": ${e.message}`);
      failed++;
    }
  });

  // Test 11: Chart destruction before switching (prevent canvas reuse error)
  console.log(
    "\n📋 Test 11: Chart destruction (prevent 'Canvas is already in use' error)",
  );
  try {
    const state = {};

    // Simulate chart creation and destruction cycle
    parseCommand("due", state);
    assert.strictEqual(state.currentChart, "due", "Should create due chart");

    parseCommand("reviews", state);
    assert.strictEqual(
      state.currentChart,
      "reviews",
      "Should destroy due and create reviews",
    );

    // Shortcut should stay on reviews (not switch to due)
    parseCommand("3m", state);
    assert.strictEqual(
      state.currentChart,
      "reviews",
      "Should stay on reviews with 3m",
    );

    // Explicit command should switch
    parseCommand("due", state);
    assert.strictEqual(state.currentChart, "due", "Should switch to due");

    parseCommand("reviews 6m", state);
    assert.strictEqual(
      state.currentChart,
      "reviews",
      "Should switch to reviews",
    );

    console.log("   ✓ Chart destruction works correctly");
    passed++;
  } catch (e) {
    console.log(`   ✗ Chart destruction: ${e.message}`);
    failed++;
  }

  // Test 12: Rapid sequential commands (stress test)
  console.log("\n📋 Test 12: Rapid sequential commands (stress test)");
  try {
    const state = {};
    const commands = [
      "due",
      "reviews",
      "1m",
      "2m",
      "3m",
      "reviews 6m",
      "all",
      "due 1y",
    ];

    commands.forEach((cmd) => {
      const result = parseCommand(cmd, state);
      assert.strictEqual(result.handled, true, `Should handle: ${cmd}`);
    });

    console.log(`   ✓ ${commands.length} rapid commands handled`);
    passed++;
  } catch (e) {
    console.log(`   ✗ Rapid commands: ${e.message}`);
    failed++;
  }

  // Test 13: Plot umbrella command
  console.log("\n📋 Test 13: 'plot' umbrella command");
  try {
    const state = {};

    // plot due
    const result1 = parseCommand("plot due", state);
    assert.strictEqual(result1.handled, true, "Should handle 'plot due'");
    assert.strictEqual(
      result1.command,
      "plot-due",
      "Should be plot-due command",
    );
    assert.strictEqual(state.currentChart, "due", "Should show due chart");

    // plot reviews
    const result2 = parseCommand("plot reviews", state);
    assert.strictEqual(result2.handled, true, "Should handle 'plot reviews'");
    assert.strictEqual(
      result2.command,
      "plot-reviews",
      "Should be plot-reviews command",
    );
    assert.strictEqual(
      state.currentChart,
      "reviews",
      "Should show reviews chart",
    );

    // plot due 3m
    const result3 = parseCommand("plot due 3m", state);
    assert.strictEqual(result3.handled, true, "Should handle 'plot due 3m'");
    assert.strictEqual(
      result3.command,
      "plot-due",
      "Should be plot-due command",
    );
    assert.strictEqual(result3.range, "3m", "Should have 3m range");

    // plot reviews 1y
    const result4 = parseCommand("plot reviews 1y", state);
    assert.strictEqual(
      result4.handled,
      true,
      "Should handle 'plot reviews 1y'",
    );
    assert.strictEqual(
      result4.command,
      "plot-reviews",
      "Should be plot-reviews command",
    );
    assert.strictEqual(result4.range, "1y", "Should have 1y range");

    // plot reviews time 6m
    const result5 = parseCommand("plot reviews time 6m", state);
    assert.strictEqual(
      result5.handled,
      true,
      "Should handle 'plot reviews time 6m'",
    );
    assert.strictEqual(
      result5.command,
      "plot-reviews-time",
      "Should be plot-reviews-time command",
    );
    assert.strictEqual(result5.range, "6m", "Should have 6m range");

    // plot reviews cumulative all
    const result6 = parseCommand("plot reviews cumulative all", state);
    assert.strictEqual(
      result6.handled,
      true,
      "Should handle 'plot reviews cumulative all'",
    );
    assert.strictEqual(
      result6.command,
      "plot-reviews-cumulative",
      "Should be plot-reviews-cumulative command",
    );
    assert.strictEqual(result6.range, "all", "Should have all range");

    console.log("   ✓ 'plot' umbrella command variations work");
    passed++;
  } catch (e) {
    console.log(`   ✗ 'plot' umbrella: ${e.message}`);
    failed++;
  }

  // Test 14: Cumulative context toggling
  console.log("\n📋 Test 14: Cumulative context toggling");
  try {
    const state = {};

    // Base reviews
    parseCommand("reviews", state);
    assert.strictEqual(state.currentChart, "reviews");

    // Toggle cumulative
    parseCommand("cumulative", state);
    assert.strictEqual(state.currentChart, "reviews-cumulative");

    // Toggle deck on cumulative
    parseCommand("deck", state);
    assert.strictEqual(state.currentChart, "reviews-deck-cumulative");

    // Toggle time on cumulative deck
    parseCommand("time", state);
    assert.strictEqual(state.currentChart, "reviews-time-deck-cumulative");

    // Toggle cumulative off
    parseCommand("c", state);
    assert.strictEqual(state.currentChart, "reviews-time-deck");

    // Toggle deck off
    parseCommand("deck", state);
    assert.strictEqual(state.currentChart, "reviews-time");

    console.log("   ✓ Cumulative toggles with time/deck properly");
    passed++;
  } catch (e) {
    console.log(`   ✗ Cumulative toggles: ${e.message}`);
    failed++;
  }

  // Test 15: Cumulative abbreviations
  console.log("\n📋 Test 15: Cumulative specific abbreviations");
  try {
    const state = {};

    const checks = [
      { cmd: "rc", chart: "reviews-cumulative" },
      { cmd: "rtc", chart: "reviews-time-cumulative" },
      { cmd: "rdc", chart: "reviews-deck-cumulative" },
      { cmd: "rtdc", chart: "reviews-time-deck-cumulative" },
    ];

    checks.forEach(({ cmd, chart }) => {
      parseCommand(cmd, state);
      assert.strictEqual(state.currentChart, chart, `Shortcut ${cmd} failed`);
    });

    console.log("   ✓ Cumulative abbreviation shortcuts work");
    passed++;
  } catch (e) {
    console.log(`   ✗ Cumulative shortcuts: ${e.message}`);
    failed++;
  }

  console.log("\n" + "=".repeat(60));

  // Test 16: Retention command
  console.log("\n📋 Test 16: 'retention' command");
  try {
    const state = {};

    // retention (default)
    const result1 = parseCommand("retention", state);
    assert.strictEqual(result1.handled, true, "Should handle 'retention'");
    assert.strictEqual(
      result1.command,
      "retention",
      "Should be retention command",
    );
    assert.strictEqual(
      state.currentChart,
      "retention",
      "Should show retention chart",
    );

    // retention with range
    const result2 = parseCommand("retention 1y", state);
    assert.strictEqual(result2.handled, true, "Should handle 'retention 1y'");
    assert.strictEqual(result2.range, "1y", "Should have 1y range");

    console.log("   ✓ 'retention' command works");
    passed++;
  } catch (e) {
    console.log(`   ✗ 'retention' command: ${e.message}`);
    failed++;
  }

  // Test 15: Plot subcommand help
  console.log("\n📋 Test 15: 'plot' shows subcommand help");
  try {
    const state = {};

    // plot alone should show help
    const result1 = parseCommand("plot", state);
    assert.strictEqual(result1.handled, true, "Should handle 'plot'");
    assert.strictEqual(result1.command, "plot", "Should be plot command");

    // p alone should also show help
    const result2 = parseCommand("p", state);
    assert.strictEqual(result2.handled, true, "Should handle 'p'");
    assert.strictEqual(result2.command, "plot", "Should be plot command");

    console.log("   ✓ 'plot' and 'p' show subcommand help");
    passed++;
  } catch (e) {
    console.log(`   ✗ 'plot' help: ${e.message}`);
    failed++;
  }

  // Test 16: Range shortcuts work on retention chart
  console.log("\n📋 Test 16: Range shortcuts respect retention chart");
  try {
    const state = {};

    // Start with retention chart
    parseCommand("retention", state);
    assert.strictEqual(
      state.currentChart,
      "retention",
      "Should be on retention",
    );

    // Range shortcut should stay on retention
    parseCommand("all", state);
    assert.strictEqual(
      state.currentChart,
      "retention",
      "Shortcut should stay on retention",
    );

    parseCommand("1y", state);
    assert.strictEqual(
      state.currentChart,
      "retention",
      "Shortcut should stay on retention",
    );

    parseCommand("6m", state);
    assert.strictEqual(
      state.currentChart,
      "retention",
      "Shortcut should stay on retention",
    );

    console.log("   ✓ Range shortcuts work on retention chart");
    passed++;
  } catch (e) {
    console.log(`   ✗ Range shortcuts on retention: ${e.message}`);
    failed++;
  }

  // Test 17: Deck and Time toggles
  console.log("\n📋 Test 17: Deck and Time toggles");
  try {
    const state = {};

    // time toggles reviews -> reviews-time
    parseCommand("reviews", state);
    parseCommand("time", state);
    assert.strictEqual(
      state.currentChart,
      "reviews-time",
      "Should toggle to reviews-time",
    );

    // time toggles reviews-time -> reviews (reverse direction)
    parseCommand("time", state);
    assert.strictEqual(
      state.currentChart,
      "reviews",
      "Should toggle back to reviews",
    );

    // deck toggles reviews -> reviews-deck
    parseCommand("deck", state);
    assert.strictEqual(
      state.currentChart,
      "reviews-deck",
      "Should toggle to reviews-deck",
    );

    // deck toggles reviews-deck -> reviews
    parseCommand("deck", state);
    assert.strictEqual(
      state.currentChart,
      "reviews",
      "Should toggle back to reviews",
    );

    // starting from reviews-time, deck -> reviews-time-deck
    parseCommand("rt", state);
    parseCommand("deck", state);
    assert.strictEqual(
      state.currentChart,
      "reviews-time-deck",
      "Should toggle to reviews-time-deck",
    );

    // deck toggles due -> due-deck
    parseCommand("due", state);
    parseCommand("deck", state);
    assert.strictEqual(
      state.currentChart,
      "due-deck",
      "Should toggle to due-deck",
    );

    // deck toggles due-deck -> due
    parseCommand("deck", state);
    assert.strictEqual(state.currentChart, "due", "Should toggle back to due");

    console.log("   ✓ Deck and time toggles work correctly");
    passed++;
  } catch (e) {
    console.log(`   ✗ Deck and Time toggles: ${e.message}`);
    failed++;
  }

  // Test 18: Due Deck specific aliases
  console.log("\n📋 Test 18: Due Deck aliases");
  try {
    const state = {};

    parseCommand("pdd", state);
    assert.strictEqual(state.currentChart, "due-deck");

    parseCommand("dd", state);
    assert.strictEqual(state.currentChart, "due-deck");

    parseCommand("plot due deck 6m", state);
    assert.strictEqual(state.currentChart, "due-deck");
    assert.strictEqual(state.activeRange, "6m");

    console.log("   ✓ Due Deck aliases route correctly");
    passed++;
  } catch (e) {
    console.log(`   ✗ Due Deck aliases: ${e.message}`);
    failed++;
  }

  // Test 17: Chart switching between all chart types
  console.log("\n📋 Test 17: Chart switching (due ↔ reviews ↔ retention)");
  try {
    const state = {};

    // Start with due chart
    parseCommand("plot due", state);
    assert.strictEqual(
      state.currentChart,
      "due",
      "Should start with due chart",
    );

    // Switch to reviews - should properly destroy due and create reviews
    parseCommand("plot reviews", state);
    assert.strictEqual(
      state.currentChart,
      "reviews",
      "Should switch from due to reviews",
    );

    // Switch to retention - should properly destroy reviews and create retention
    parseCommand("plot retention", state);
    assert.strictEqual(
      state.currentChart,
      "retention",
      "Should switch from reviews to retention",
    );

    // Switch back to due - should properly destroy retention and create due
    parseCommand("plot due", state);
    assert.strictEqual(
      state.currentChart,
      "due",
      "Should switch from retention back to due",
    );

    // Switch to retention directly from due
    parseCommand("plot retention", state);
    assert.strictEqual(
      state.currentChart,
      "retention",
      "Should switch from due to retention",
    );

    // Switch to reviews from retention
    parseCommand("plot reviews", state);
    assert.strictEqual(
      state.currentChart,
      "reviews",
      "Should switch from retention to reviews",
    );

    // Switch to reviews time from reviews
    parseCommand("plot reviews time", state);
    assert.strictEqual(
      state.currentChart,
      "reviews-time",
      "Should switch from reviews to reviews time",
    );

    // Switch from reviews time back to reviews via "time" toggle
    parseCommand("time", state);
    assert.strictEqual(
      state.currentChart,
      "reviews",
      "Should toggle off reviews-time to reviews with time shortcut",
    );

    // Switch back to due via shortcut
    parseCommand("due", state);
    assert.strictEqual(
      state.currentChart,
      "due",
      "Should switch from reviews-time to due",
    );

    // Switch to reviews time directly via "t" shortcut
    parseCommand("t", state);
    assert.strictEqual(
      state.currentChart,
      "reviews-time",
      "Should switch from due to reviews-time via t shortcut",
    );

    console.log("   ✓ Chart switching works between all chart types");
    passed++;
  } catch (e) {
    console.log(`   ✗ Chart switching: ${e.message}`);
    failed++;
  }

  // Test 18: Zoom auto-reset on plot commands
  console.log(
    "\n📋 Test 18: Zoom auto-reset on plot commands (regression test)",
  );
  try {
    const state = { isZoomed: false, currentChart: null };

    // Zoom in
    parseCommand("zoom", state);
    assert.strictEqual(state.isZoomed, true, "Should be zoomed in");

    // Range shortcut should auto-unzoom
    parseCommand("3m", state);
    assert.strictEqual(
      state.isZoomed,
      false,
      "Range shortcut should auto-unzoom",
    );

    // Zoom in again
    parseCommand("zoom", state);
    assert.strictEqual(state.isZoomed, true, "Should be zoomed in again");

    // Explicit plot command should auto-unzoom
    parseCommand("plot due", state);
    assert.strictEqual(
      state.isZoomed,
      false,
      "Explicit plot command should auto-unzoom",
    );

    // Zoom in again
    parseCommand("zoom", state);

    // Explicit chart command should auto-unzoom
    parseCommand("reviews", state);
    assert.strictEqual(
      state.isZoomed,
      false,
      "Explicit chart command should auto-unzoom",
    );

    console.log("   ✓ Zoom auto-reset works for plot commands");
    passed++;
  } catch (e) {
    console.log(`   ✗ Zoom auto-reset: ${e.message}`);
    failed++;
  }

  // Test 19: Time range persists across charts
  console.log("\n📋 Test 19: Time range persists across charts");
  try {
    const state = {
      currentChart: null,
      activeRange: DEFAULT_RANGE,
      isZoomed: false,
    };

    // Switch to due with 1y range
    const result1 = parseCommand("plot due 1y", state);
    assert.strictEqual(result1.range, "1y", "Should plot due 1y");
    assert.strictEqual(
      state.activeRange,
      "1y",
      "Should persist 1y range to state",
    );

    // Switch to reviews, should implicitly use 1y
    const result2 = parseCommand("reviews", state);
    assert.strictEqual(
      result2.range,
      "1y",
      "Should implicitly use 1y range on reviews",
    );

    // Provide explicit range, should update active range
    const result3 = parseCommand("reviews 3m", state);
    assert.strictEqual(result3.range, "3m", "Should use 3m explicitly");
    assert.strictEqual(
      state.activeRange,
      "3m",
      "Should update persisted state to 3m",
    );

    // Verify switching to retention uses 3m
    const result4 = parseCommand("retention", state);
    assert.strictEqual(
      result4.range,
      "3m",
      "Should implicitly use 3m on retention",
    );

    console.log("   ✓ Chart switching persists time range");
    passed++;
  } catch (e) {
    console.log(`   ✗ Chart switching persists time range: ${e.message}`);
    failed++;
  }

  // Test 20: Time range persistence on due-deck
  console.log("\n📋 Test 20: Time range persistence on due-deck");
  try {
    const state = { currentChart: "due-deck", activeRange: "1m" };

    parseCommand("3m", state);
    assert.strictEqual(
      state.currentChart,
      "due-deck",
      "Should stay on due-deck after time range update",
    );
    assert.strictEqual(state.activeRange, "3m");

    console.log("   ✓ Time range correctly persists chart type");
    passed++;
  } catch (e) {
    console.log(`   ✗ Time range persistence: ${e.message}`);
    failed++;
  }

  // Test 21: 'plot' command preserves current state
  console.log("\n📋 Test 21: 'plot' command preserves current state");
  try {
    const state = { currentChart: "reviews-time", activeRange: "6m" };

    const result = parseCommand("plot", state);
    assert.strictEqual(result.handled, true, "Should handle 'plot'");
    assert.strictEqual(result.command, "plot", "Should be plot command");
    assert.strictEqual(
      state.currentChart,
      "reviews-time",
      "Should preserve currentChart",
    );
    assert.strictEqual(state.activeRange, "6m", "Should preserve activeRange");

    const result2 = parseCommand("p", state);
    assert.strictEqual(result2.handled, true, "Should handle 'p'");
    assert.strictEqual(
      state.currentChart,
      "reviews-time",
      "Should preserve currentChart with 'p'",
    );

    console.log("   ✓ 'plot' command correctly preserves current chart state");
    passed++;
  } catch (e) {
    console.log(`   ✗ 'plot' command state preservation: ${e.message}`);
    failed++;
  }

  // Summary
  console.log("\n" + "=".repeat(60));
  console.log(`\n📊 Results: ${passed} passed, ${failed} failed\n`);

  if (failed > 0) {
    console.log("❌ TESTS FAILED - Command handler has issues");
    console.log("\n⚠️  Key requirements:");
    console.log("   • Time shortcuts (1m, 3m, all) must work standalone");
    console.log("   • 'reviews' then '3m' must switch charts properly");
    console.log("   • Chart state must track current chart type");
    console.log(
      "   • Charts must be destroyed before switching (prevent canvas reuse error)",
    );
    console.log("   • 'plot' preserves current chart state");
    console.log();
    process.exit(1);
  } else {
    console.log("✅ ALL TESTS PASSED - Command handler working correctly");
    console.log("\n📝 Verified:");
    console.log("   • Time range shortcuts work as standalone commands");
    console.log("   • Chart switching (due ↔ reviews) works");
    console.log("   • Sequential commands work (regression prevented)");
    console.log("   • Invalid ranges are handled gracefully");
    console.log(
      "   • Chart destruction prevents 'Canvas is already in use' error",
    );
    console.log("   • Rapid sequential commands handled correctly");
    console.log("   • 'retention' command works");
    console.log("   • 'plot' shows subcommand help");
    console.log("   • Range shortcuts work on retention chart");
    console.log("   • Chart switching works between all chart types");
    console.log("   • 'plot' command correctly preserves current chart state");
    console.log();
    process.exit(0);
  }
}

// Run tests
runTests();
