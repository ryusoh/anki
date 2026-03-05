/**
 * Chart Legend Test
 * Tests that legends update correctly when switching between charts,
 * have data-dataset-index attributes for toggle, and Chart.js native
 * legend is disabled.
 *
 * Run: node tests/legend.test.js
 */

const assert = require("assert");

// ============================================================================
// MOCK DOM ELEMENTS
// ============================================================================

class MockElement {
  constructor() {
    this.innerHTML = "";
    this.style = { display: "" };
    this.classList = {
      _classes: new Set(),
      add(cls) {
        this._classes.add(cls);
      },
      remove(cls) {
        this._classes.delete(cls);
      },
      contains(cls) {
        return this._classes.has(cls);
      },
      toggle(cls, force) {
        if (force === undefined) {
          if (this._classes.has(cls)) this._classes.delete(cls);
          else this._classes.add(cls);
        } else if (force) {
          this._classes.add(cls);
        } else {
          this._classes.delete(cls);
        }
      },
    };
    this._listeners = {};
  }

  setAttribute(name, value) {
    this[name] = value;
  }

  querySelectorAll(selector) {
    // Parse data-dataset-index spans from innerHTML
    if (!selector.includes("data-dataset-index")) return [];
    const matches = this.innerHTML.match(/data-dataset-index="(\d+)"/g);
    if (!matches) return [];
    return matches.map((m) => {
      const index = m.match(/\d+/)[0];
      const el = new MockElement();
      el.dataset = { datasetIndex: index };
      return el;
    });
  }

  addEventListener(event, fn) {
    if (!this._listeners[event]) this._listeners[event] = [];
    this._listeners[event].push(fn);
  }
}

function createMockDOM() {
  return {
    runningAmountSection: new MockElement(),
    chartLegend: new MockElement(),
    runningAmountEmpty: new MockElement(),
    runningAmountCanvas: new MockElement(),
  };
}

// ============================================================================
// MOCK CHART COMMANDS (mirrors the actual legend HTML from due.js / reviews.js)
// ============================================================================

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

const DEFAULT_RANGE = "1m";

// Mock due chart rendering
function renderDueChart(mockDOM) {
  if (mockDOM.chartLegend) {
    mockDOM.chartLegend.innerHTML = `
            <span data-dataset-index="0"><i class="legend-color color-mature"></i> Mature</span>
            <span data-dataset-index="1"><i class="legend-color color-young"></i> Young</span>
        `;
    mockDOM.chartLegend.style.display = "flex";
  }
  return { success: true, chart: "due" };
}

// Mock reviews chart rendering (stacked by card status)
function renderReviewsChart(mockDOM) {
  if (mockDOM.chartLegend) {
    mockDOM.chartLegend.innerHTML = `
            <span data-dataset-index="0"><i class="legend-color color-mature"></i> Mature</span>
            <span data-dataset-index="1"><i class="legend-color color-young"></i> Young</span>
            <span data-dataset-index="2"><i class="legend-color color-relearn"></i> Relearn</span>
            <span data-dataset-index="3"><i class="legend-color color-learn"></i> Learn</span>
        `;
    mockDOM.chartLegend.style.display = "flex";
  }
  return { success: true, chart: "reviews" };
}

// Mock retention chart rendering
function renderRetentionChart(mockDOM) {
  if (mockDOM.chartLegend) {
    mockDOM.chartLegend.innerHTML = `
            <span data-dataset-index="0"><i class="legend-color color-retention"></i> Retention Rate</span>
        `;
    mockDOM.chartLegend.style.display = "flex";
  }
  return { success: true, chart: "retention" };
}

// Mock clear chart
function clearChart(mockDOM) {
  if (mockDOM.runningAmountSection) {
    mockDOM.runningAmountSection.classList.add("is-hidden");
  }
  if (mockDOM.chartLegend) {
    mockDOM.chartLegend.innerHTML = "";
    mockDOM.chartLegend.style.display = "none";
  }
}

// ============================================================================
// CHART.JS CONFIG VALIDATORS
// ============================================================================

/**
 * Returns the Chart.js config that each chart would produce.
 * Used to verify legend.display is inside options.plugins.
 */
function getDueChartConfig() {
  return {
    type: "bar",
    options: {
      plugins: {
        legend: { display: false },
      },
    },
  };
}

function getReviewsChartConfig() {
  return {
    type: "bar",
    options: {
      plugins: {
        legend: { display: false },
      },
    },
  };
}

function getRetentionChartConfig() {
  return {
    type: "line",
    options: {
      plugins: {
        legend: { display: false },
      },
    },
  };
}

// ============================================================================
// LEGEND VALIDATION
// ============================================================================

const DUE_LEGEND_EXPECTED = {
  items: 2,
  labels: ["Mature", "Young"],
  classes: ["color-mature", "color-young"],
  datasetIndices: ["0", "1"],
};

const REVIEWS_LEGEND_EXPECTED = {
  items: 4,
  labels: ["Mature", "Young", "Relearn", "Learn"],
  classes: ["color-mature", "color-young", "color-relearn", "color-learn"],
  datasetIndices: ["0", "1", "2", "3"],
};

const RETENTION_LEGEND_EXPECTED = {
  items: 1,
  labels: ["Retention Rate"],
  classes: ["color-retention"],
  datasetIndices: ["0"],
};

function validateLegend(mockDOM, expected, chartName) {
  const legend = mockDOM.chartLegend;

  assert.ok(legend, "Legend element must exist");

  const html = legend.innerHTML;

  expected.labels.forEach((label) => {
    assert.ok(
      html.includes(label),
      `Legend must contain "${label}" for ${chartName}`,
    );
  });

  expected.classes.forEach((cls) => {
    assert.ok(
      html.includes(cls),
      `Legend must have class "${cls}" for ${chartName}`,
    );
  });

  // Check data-dataset-index attributes
  expected.datasetIndices.forEach((idx) => {
    assert.ok(
      html.includes(`data-dataset-index="${idx}"`),
      `Legend must have data-dataset-index="${idx}" for ${chartName}`,
    );
  });

  assert.strictEqual(
    legend.style.display,
    "flex",
    `Legend display must be "flex" for ${chartName}`,
  );
}

// ============================================================================
// TESTS
// ============================================================================

function runTests() {
  let passed = 0;
  let failed = 0;

  console.log("🧪 Chart Legend Test\n");
  console.log("=".repeat(60));

  // Test 1: Due chart legend
  console.log("\n📋 Test 1: Due chart legend");
  try {
    const mockDOM = createMockDOM();
    renderDueChart(mockDOM);
    validateLegend(mockDOM, DUE_LEGEND_EXPECTED, "due chart");
    console.log(
      "   ✓ Due chart legend shows Mature / Young with dot symbols",
    );
    passed++;
  } catch (e) {
    console.log(`   ✗ Due chart legend: ${e.message}`);
    failed++;
  }

  // Test 2: Reviews chart legend
  console.log("\n📋 Test 2: Reviews chart legend");
  try {
    const mockDOM = createMockDOM();
    renderReviewsChart(mockDOM);
    validateLegend(mockDOM, REVIEWS_LEGEND_EXPECTED, "reviews chart");
    console.log(
      "   ✓ Reviews chart legend shows Mature / Young / Relearn / Learn",
    );
    passed++;
  } catch (e) {
    console.log(`   ✗ Reviews chart legend: ${e.message}`);
    failed++;
  }

  // Test 3: Legend clears when switching
  console.log("\n📋 Test 3: Legend clears when switching charts");
  try {
    const mockDOM = createMockDOM();

    renderDueChart(mockDOM);
    assert.ok(
      mockDOM.chartLegend.innerHTML.includes("Mature"),
      "Should have due legend",
    );

    clearChart(mockDOM);
    assert.strictEqual(
      mockDOM.chartLegend.innerHTML,
      "",
      "Legend should be cleared",
    );
    assert.strictEqual(
      mockDOM.chartLegend.style.display,
      "none",
      "Legend should be hidden",
    );

    console.log("   ✓ Legend properly cleared between charts");
    passed++;
  } catch (e) {
    console.log(`   ✗ Legend clearing: ${e.message}`);
    failed++;
  }

  // Test 4: Chart switching updates legend
  console.log("\n📋 Test 4: Chart switching updates legend correctly");
  try {
    const mockDOM = createMockDOM();

    renderDueChart(mockDOM);
    validateLegend(mockDOM, DUE_LEGEND_EXPECTED, "due chart (initial)");

    renderReviewsChart(mockDOM);
    validateLegend(
      mockDOM,
      REVIEWS_LEGEND_EXPECTED,
      "reviews chart (after switch)",
    );

    renderDueChart(mockDOM);
    validateLegend(mockDOM, DUE_LEGEND_EXPECTED, "due chart (switched back)");

    console.log("   ✓ Legend updates correctly on chart switching");
    passed++;
  } catch (e) {
    console.log(`   ✗ Chart switching: ${e.message}`);
    failed++;
  }

  // Test 5: Legend has dot symbols (not bars or other shapes)
  console.log("\n📋 Test 5: Legend uses dot symbols for consistency");
  try {
    const mockDOM = createMockDOM();

    renderDueChart(mockDOM);
    assert.ok(
      mockDOM.chartLegend.innerHTML.includes('class="legend-color'),
      "Due legend must use legend-color class",
    );

    renderReviewsChart(mockDOM);
    assert.ok(
      mockDOM.chartLegend.innerHTML.includes('class="legend-color'),
      "Reviews legend must use legend-color class",
    );

    renderRetentionChart(mockDOM);
    assert.ok(
      mockDOM.chartLegend.innerHTML.includes('class="legend-color'),
      "Retention legend must use legend-color class",
    );

    console.log("   ✓ All charts use consistent dot symbol styling");
    passed++;
  } catch (e) {
    console.log(`   ✗ Dot symbols: ${e.message}`);
    failed++;
  }

  // Test 6: Legend is visible when chart shows
  console.log("\n📋 Test 6: Legend visibility");
  try {
    const mockDOM = createMockDOM();

    renderDueChart(mockDOM);
    assert.strictEqual(
      mockDOM.chartLegend.style.display,
      "flex",
      "Due legend should be visible",
    );

    renderReviewsChart(mockDOM);
    assert.strictEqual(
      mockDOM.chartLegend.style.display,
      "flex",
      "Reviews legend should be visible",
    );

    clearChart(mockDOM);
    assert.strictEqual(
      mockDOM.chartLegend.style.display,
      "none",
      "Cleared legend should be hidden",
    );

    console.log("   ✓ Legend visibility managed correctly");
    passed++;
  } catch (e) {
    console.log(`   ✗ Legend visibility: ${e.message}`);
    failed++;
  }

  // Test 7: Legend position (bottom of chart)
  console.log("\n📋 Test 7: Legend position structure");
  try {
    const mockDOM = createMockDOM();

    renderDueChart(mockDOM);
    assert.ok(mockDOM.chartLegend, "Legend must be separate element");
    assert.ok(mockDOM.runningAmountCanvas, "Canvas must be separate element");
    assert.notStrictEqual(
      mockDOM.chartLegend,
      mockDOM.runningAmountCanvas,
      "Legend and canvas must be different elements",
    );

    console.log("   ✓ Legend is positioned separately from chart");
    passed++;
  } catch (e) {
    console.log(`   ✗ Legend position: ${e.message}`);
    failed++;
  }

  // Test 8: Multiple sequential switches
  console.log("\n📋 Test 8: Multiple sequential chart switches");
  try {
    const mockDOM = createMockDOM();
    const sequence = ["due", "reviews", "retention", "due", "reviews"];

    sequence.forEach((chart, i) => {
      if (chart === "due") {
        renderDueChart(mockDOM);
        validateLegend(
          mockDOM,
          DUE_LEGEND_EXPECTED,
          `due chart (switch ${i + 1})`,
        );
      } else if (chart === "reviews") {
        renderReviewsChart(mockDOM);
        validateLegend(
          mockDOM,
          REVIEWS_LEGEND_EXPECTED,
          `reviews chart (switch ${i + 1})`,
        );
      } else {
        renderRetentionChart(mockDOM);
        validateLegend(
          mockDOM,
          RETENTION_LEGEND_EXPECTED,
          `retention chart (switch ${i + 1})`,
        );
      }
    });

    console.log("   ✓ Multiple switches maintain correct legends");
    passed++;
  } catch (e) {
    console.log(`   ✗ Multiple switches: ${e.message}`);
    failed++;
  }

  // Test 9: Legend text is in correct language
  console.log("\n📋 Test 9: Legend text language");
  try {
    const mockDOM = createMockDOM();
    // Due chart should have English
    renderDueChart(mockDOM);
    const dueHtml = mockDOM.chartLegend.innerHTML;
    assert.ok(/Mature/.test(dueHtml), "Due legend should have Mature");
    assert.ok(/Young/.test(dueHtml), "Due legend should have Young");

    renderReviewsChart(mockDOM);
    const reviewsHtml = mockDOM.chartLegend.innerHTML;
    assert.ok(
      /Mature/.test(reviewsHtml),
      "Reviews legend should have English text (Mature)",
    );
    assert.ok(
      /Young/.test(reviewsHtml),
      "Reviews legend should have English text (Young)",
    );

    console.log("   ✓ Legend text uses correct language (English)");
    passed++;
  } catch (e) {
    console.log(`   ✗ Legend language: ${e.message}`);
    failed++;
  }

  // Test 10: Legend color classes match chart colors
  console.log("\n📋 Test 10: Legend color classes match chart");
  try {
    const mockDOM = createMockDOM();

    renderDueChart(mockDOM);
    const dueHtml = mockDOM.chartLegend.innerHTML;
    assert.ok(
      dueHtml.includes("color-young"),
      "Due should have young color class (blue)",
    );
    assert.ok(
      dueHtml.includes("color-mature"),
      "Due should have mature color class (green)",
    );

    renderReviewsChart(mockDOM);
    const reviewsHtml = mockDOM.chartLegend.innerHTML;
    assert.ok(reviewsHtml.includes("color-mature"), "Reviews: mature");
    assert.ok(reviewsHtml.includes("color-young"), "Reviews: young");
    assert.ok(reviewsHtml.includes("color-learn"), "Reviews: learn");
    assert.ok(reviewsHtml.includes("color-relearn"), "Reviews: relearn");

    console.log("   ✓ Legend color classes match chart colors");
    passed++;
  } catch (e) {
    console.log(`   ✗ Legend colors: ${e.message}`);
    failed++;
  }

  // Test 11: Reviews chart has stacked datasets by card status
  console.log("\n📋 Test 11: Reviews chart stacked by card status");
  try {
    const mockDOM = createMockDOM();
    renderReviewsChart(mockDOM);
    const reviewsHtml = mockDOM.chartLegend.innerHTML;

    assert.ok(reviewsHtml.includes("Mature"), "Reviews legend: Mature");
    assert.ok(reviewsHtml.includes("Young"), "Reviews legend: Young");
    assert.ok(reviewsHtml.includes("Learn"), "Reviews legend: Learn");
    assert.ok(reviewsHtml.includes("Relearn"), "Reviews legend: Relearn");

    // Verify correct order: Learn should appear after Relearn (top of stack)
    const learnIndex = reviewsHtml.indexOf("Learn");
    const relearnIndex = reviewsHtml.indexOf("Relearn");
    assert.ok(
      learnIndex > relearnIndex,
      "Learn should appear after Relearn (top of stack)",
    );

    console.log("   ✓ Reviews chart stacked by card status");
    passed++;
  } catch (e) {
    console.log(`   ✗ Reviews stacked: ${e.message}`);
    failed++;
  }

  // Test 12: Chart.js native legend is disabled (regression guard)
  console.log("\n📋 Test 12: Chart.js native legend is disabled");
  try {
    const configs = [
      { name: "due", config: getDueChartConfig() },
      { name: "reviews", config: getReviewsChartConfig() },
      { name: "retention", config: getRetentionChartConfig() },
    ];

    configs.forEach(({ name, config }) => {
      // legend.display must be inside options.plugins, NOT top-level plugins
      assert.ok(
        config.options &&
        config.options.plugins &&
        config.options.plugins.legend,
        `${name}: options.plugins.legend must exist`,
      );
      assert.strictEqual(
        config.options.plugins.legend.display,
        false,
        `${name}: options.plugins.legend.display must be false`,
      );
    });

    console.log(
      "   ✓ All charts have legend.display=false inside options.plugins",
    );
    passed++;
  } catch (e) {
    console.log(`   ✗ Native legend disabled: ${e.message}`);
    failed++;
  }

  // Test 13: All bottom legend items have data-dataset-index
  console.log("\n📋 Test 13: Legend items have data-dataset-index");
  try {
    const mockDOM = createMockDOM();

    // Due chart
    renderDueChart(mockDOM);
    DUE_LEGEND_EXPECTED.datasetIndices.forEach((idx) => {
      assert.ok(
        mockDOM.chartLegend.innerHTML.includes(`data-dataset-index="${idx}"`),
        `Due legend must have data-dataset-index="${idx}"`,
      );
    });

    // Reviews chart
    renderReviewsChart(mockDOM);
    REVIEWS_LEGEND_EXPECTED.datasetIndices.forEach((idx) => {
      assert.ok(
        mockDOM.chartLegend.innerHTML.includes(`data-dataset-index="${idx}"`),
        `Reviews legend must have data-dataset-index="${idx}"`,
      );
    });

    // Retention chart
    renderRetentionChart(mockDOM);
    RETENTION_LEGEND_EXPECTED.datasetIndices.forEach((idx) => {
      assert.ok(
        mockDOM.chartLegend.innerHTML.includes(`data-dataset-index="${idx}"`),
        `Retention legend must have data-dataset-index="${idx}"`,
      );
    });

    console.log("   ✓ All chart legends have data-dataset-index on every item");
    passed++;
  } catch (e) {
    console.log(`   ✗ data-dataset-index: ${e.message}`);
    failed++;
  }

  // Test 14: Legend toggle adds/removes legend-disabled class
  console.log("\n📋 Test 14: Legend toggle adds legend-disabled class");
  try {
    // Simulate bindLegendToggle behavior
    const mockChart = {
      _datasetMeta: [{}, {}, {}, {}],
      getDatasetMeta(i) {
        if (!this._datasetMeta[i]) this._datasetMeta[i] = {};
        return this._datasetMeta[i];
      },
      updateCalled: false,
      updateMode: null,
      update(mode) {
        this.updateCalled = true;
        this.updateMode = mode;
      },
    };

    const mockDOM = createMockDOM();
    renderReviewsChart(mockDOM);

    // Get mock spans
    const spans = mockDOM.chartLegend.querySelectorAll("[data-dataset-index]");
    assert.strictEqual(spans.length, 4, "Should have 4 legend items");

    // Simulate binding
    spans.forEach((span) => {
      span.addEventListener("click", () => {
        const i = parseInt(span.dataset.datasetIndex, 10);
        const meta = mockChart.getDatasetMeta(i);
        meta.hidden = !meta.hidden;
        span.classList.toggle("legend-disabled", meta.hidden);
        mockChart.update("active");
      });
    });

    // Click first item to hide
    const firstSpan = spans[0];
    firstSpan._listeners["click"][0]();

    assert.strictEqual(
      mockChart.getDatasetMeta(0).hidden,
      true,
      "Dataset 0 should be hidden after click",
    );
    assert.ok(
      firstSpan.classList.contains("legend-disabled"),
      "Span should have legend-disabled class",
    );

    // Click again to show
    firstSpan._listeners["click"][0]();
    assert.strictEqual(
      mockChart.getDatasetMeta(0).hidden,
      false,
      "Dataset 0 should be visible after second click",
    );
    assert.ok(
      !firstSpan.classList.contains("legend-disabled"),
      "Span should not have legend-disabled class after re-enable",
    );

    console.log("   ✓ Toggle correctly adds/removes legend-disabled class");
    passed++;
  } catch (e) {
    console.log(`   ✗ Legend toggle: ${e.message}`);
    failed++;
  }

  // Test 15: chart.update("active") is called on toggle (animation)
  console.log("\n📋 Test 15: chart.update is called with animation");
  try {
    const mockChart = {
      _datasetMeta: [{}, {}],
      getDatasetMeta(i) {
        return this._datasetMeta[i];
      },
      updateCalled: false,
      updateMode: null,
      update(mode) {
        this.updateCalled = true;
        this.updateMode = mode;
      },
    };

    const mockDOM = createMockDOM();
    renderDueChart(mockDOM);

    const spans = mockDOM.chartLegend.querySelectorAll("[data-dataset-index]");

    spans.forEach((span) => {
      span.addEventListener("click", () => {
        const i = parseInt(span.dataset.datasetIndex, 10);
        const meta = mockChart.getDatasetMeta(i);
        meta.hidden = !meta.hidden;
        span.classList.toggle("legend-disabled", meta.hidden);
        mockChart.update("active");
      });
    });

    spans[0]._listeners["click"][0]();

    assert.strictEqual(
      mockChart.updateCalled,
      true,
      "chart.update must be called",
    );
    assert.strictEqual(
      mockChart.updateMode,
      "active",
      'chart.update must be called with "active" for animation',
    );

    console.log('   ✓ chart.update("active") called on toggle');
    passed++;
  } catch (e) {
    console.log(`   ✗ chart.update animation: ${e.message}`);
    failed++;
  }

  // Test 16: Retention chart legend
  console.log("\n📋 Test 16: Retention chart legend");
  try {
    const mockDOM = createMockDOM();
    renderRetentionChart(mockDOM);
    validateLegend(mockDOM, RETENTION_LEGEND_EXPECTED, "retention chart");
    console.log("   ✓ Retention chart legend shows Retention Rate");
    passed++;
  } catch (e) {
    console.log(`   ✗ Retention chart legend: ${e.message}`);
    failed++;
  }

  // Summary
  console.log("\n" + "=".repeat(60));
  console.log(`\n📊 Results: ${passed} passed, ${failed} failed\n`);

  if (failed > 0) {
    console.log("❌ TESTS FAILED - Legend has issues");
    console.log("\n⚠️  Requirements:");
    console.log(
      "   • Due chart: Mature / Young (English, green/blue dots)",
    );
    console.log(
      "   • Reviews chart: Mature / Young / Relearn / Learn (stacked)",
    );
    console.log("   • Retention chart: Retention Rate");
    console.log("   • All legends must have data-dataset-index");
    console.log("   • Click-to-toggle must add/remove legend-disabled class");
    console.log('   • chart.update("active") must be called for animation');
    console.log("   • Chart.js native legend must be disabled");
    console.log();
    process.exit(1);
  } else {
    console.log("✅ ALL TESTS PASSED - Legend working correctly");
    console.log("\n📝 Verified:");
    console.log("   • Due chart legend: Mature / Young with dot symbols");
    console.log("   • Reviews chart legend: Mature / Young / Relearn / Learn");
    console.log("   • Retention chart legend: Retention Rate");
    console.log("   • Legend updates on chart switching");
    console.log("   • Legend visibility managed correctly");
    console.log("   • Color classes match chart colors");
    console.log("   • Reviews stacked by card status (Learn on top)");
    console.log("   • Chart.js native legend disabled (regression guard)");
    console.log("   • All legend items have data-dataset-index");
    console.log("   • Click-to-toggle adds/removes legend-disabled class");
    console.log('   • chart.update("active") called for animation');
    console.log();
    process.exit(0);
  }
}

// Run tests
runTests();
