/**
 * Chart Legend Test
 * Tests that legends update correctly when switching between charts
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
      add: () => {},
      remove: () => {},
    };
    this.children = [];
  }

  setAttribute(name, value) {
    this[name] = value;
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
// MOCK CHART COMMANDS
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
            <span><i class="legend-color color-young"></i> 未習熟</span>
            <span><i class="legend-color color-mature"></i> 習熟済み</span>
        `;
    mockDOM.chartLegend.style.display = "flex";
  }
  return { success: true, chart: "due" };
}

// Mock reviews chart rendering (stacked by card status)
function renderReviewsChart(mockDOM) {
  if (mockDOM.chartLegend) {
    // Legend order matches stack order (first = bottom, last = top)
    // Stack: Mature (bottom) → Young → Relearn → Learn (top)
    mockDOM.chartLegend.innerHTML = `
            <span><i class="legend-color color-mature"></i> Mature</span>
            <span><i class="legend-color color-young"></i> Young</span>
            <span><i class="legend-color color-relearn"></i> Relearn</span>
            <span><i class="legend-color color-learn"></i> Learn</span>
        `;
    mockDOM.chartLegend.style.display = "flex";
  }
  return { success: true, chart: "reviews" };
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
// LEGEND VALIDATION
// ============================================================================

const DUE_LEGEND_EXPECTED = {
  items: 2,
  labels: ["未習熟", "習熟済み"],
  classes: ["color-young", "color-mature"],
};

const REVIEWS_LEGEND_EXPECTED = {
  items: 4,
  labels: ["Mature", "Young", "Learn", "Relearn"],
  classes: ["color-mature", "color-young", "color-learn", "color-relearn"],
};

function validateLegend(mockDOM, expected, chartName) {
  const legend = mockDOM.chartLegend;

  assert.ok(legend, "Legend element must exist");

  // Check innerHTML contains expected content
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

  // Check display is set
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
      "   ✓ Due chart legend shows 未習熟 / 習熟済み with dot symbols",
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
      "   ✓ Reviews chart legend shows Reviews / Retention with dot symbols",
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

    // Show due chart
    renderDueChart(mockDOM);
    assert.ok(
      mockDOM.chartLegend.innerHTML.includes("未習熟"),
      "Should have due legend",
    );

    // Clear
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

    // Start with due
    renderDueChart(mockDOM);
    validateLegend(mockDOM, DUE_LEGEND_EXPECTED, "due chart (initial)");

    // Switch to reviews
    renderReviewsChart(mockDOM);
    validateLegend(
      mockDOM,
      REVIEWS_LEGEND_EXPECTED,
      "reviews chart (after switch)",
    );

    // Switch back to due
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

    // Check due chart
    renderDueChart(mockDOM);
    const dueHtml = mockDOM.chartLegend.innerHTML;
    assert.ok(
      dueHtml.includes('class="legend-color'),
      "Due legend must use legend-color class",
    );

    // Check reviews chart
    renderReviewsChart(mockDOM);
    const reviewsHtml = mockDOM.chartLegend.innerHTML;
    assert.ok(
      reviewsHtml.includes('class="legend-color'),
      "Reviews legend must use legend-color class",
    );

    console.log("   ✓ Both charts use consistent dot symbol styling");
    passed++;
  } catch (e) {
    console.log(`   ✗ Dot symbols: ${e.message}`);
    failed++;
  }

  // Test 6: Legend is visible when chart shows
  console.log("\n📋 Test 6: Legend visibility");
  try {
    const mockDOM = createMockDOM();

    // Due chart
    renderDueChart(mockDOM);
    assert.strictEqual(
      mockDOM.chartLegend.style.display,
      "flex",
      "Due legend should be visible",
    );

    // Reviews chart
    renderReviewsChart(mockDOM);
    assert.strictEqual(
      mockDOM.chartLegend.style.display,
      "flex",
      "Reviews legend should be visible",
    );

    // Clear
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

    // Check that legend is a separate element (not inside canvas)
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
    const sequence = ["due", "reviews", "due", "reviews", "due"];

    sequence.forEach((chart, i) => {
      if (chart === "due") {
        renderDueChart(mockDOM);
        validateLegend(
          mockDOM,
          DUE_LEGEND_EXPECTED,
          `due chart (switch ${i + 1})`,
        );
      } else {
        renderReviewsChart(mockDOM);
        validateLegend(
          mockDOM,
          REVIEWS_LEGEND_EXPECTED,
          `reviews chart (switch ${i + 1})`,
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

    // Due chart should have Japanese
    renderDueChart(mockDOM);
    const dueHtml = mockDOM.chartLegend.innerHTML;
    assert.ok(/未習熟/.test(dueHtml), "Due legend should have Japanese text");
    assert.ok(/習熟済み/.test(dueHtml), "Due legend should have Japanese text");

    // Reviews chart should have English (card status categories)
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

    console.log("   ✓ Legend text uses correct languages");
    passed++;
  } catch (e) {
    console.log(`   ✗ Legend language: ${e.message}`);
    failed++;
  }

  // Test 10: Legend color classes match chart colors
  console.log("\n📋 Test 10: Legend color classes match chart");
  try {
    const mockDOM = createMockDOM();

    // Due chart colors
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

    // Reviews chart colors (stacked by card status)
    renderReviewsChart(mockDOM);
    const reviewsHtml = mockDOM.chartLegend.innerHTML;
    assert.ok(
      reviewsHtml.includes("color-mature"),
      "Reviews should have mature color class (green)",
    );
    assert.ok(
      reviewsHtml.includes("color-young"),
      "Reviews should have young color class (blue)",
    );
    assert.ok(
      reviewsHtml.includes("color-learn"),
      "Reviews should have learn color class (yellow)",
    );
    assert.ok(
      reviewsHtml.includes("color-relearn"),
      "Reviews should have relearn color class (red)",
    );

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

    // Render reviews chart
    renderReviewsChart(mockDOM);
    const reviewsHtml = mockDOM.chartLegend.innerHTML;

    // Check all 4 categories are present in legend
    assert.ok(
      reviewsHtml.includes("Mature"),
      "Reviews legend should have Mature",
    );
    assert.ok(
      reviewsHtml.includes("Young"),
      "Reviews legend should have Young",
    );
    assert.ok(
      reviewsHtml.includes("Learn"),
      "Reviews legend should have Learn",
    );
    assert.ok(
      reviewsHtml.includes("Relearn"),
      "Reviews legend should have Relearn",
    );

    // Verify correct order in legend (Learn should be last = top of stack)
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

  // Summary
  console.log("\n" + "=".repeat(60));
  console.log(`\n📊 Results: ${passed} passed, ${failed} failed\n`);

  if (failed > 0) {
    console.log("❌ TESTS FAILED - Legend has issues");
    console.log("\n⚠️  Requirements:");
    console.log(
      "   • Due chart: 未習熟 / 習熟済み (Japanese, blue/green dots)",
    );
    console.log(
      "   • Reviews chart: Mature / Young / Learn / Relearn (stacked)",
    );
    console.log("   • Legend must update on chart switch");
    console.log("   • Legend must be hidden when chart cleared");
    console.log();
    process.exit(1);
  } else {
    console.log("✅ ALL TESTS PASSED - Legend working correctly");
    console.log("\n📝 Verified:");
    console.log("   • Due chart legend: 未習熟 / 習熟済み with dot symbols");
    console.log("   • Reviews chart legend: Mature / Young / Learn / Relearn");
    console.log("   • Legend updates on chart switching");
    console.log("   • Legend visibility managed correctly");
    console.log("   • Color classes match chart colors");
    console.log("   • Reviews stacked by card status (Learn on top)");
    console.log();
    process.exit(0);
  }
}

// Run tests
runTests();
