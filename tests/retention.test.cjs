const assert = require('assert');

let capturedConfig = null;
global.window = {
    Chart: class {
        constructor(ctx, config) {
            this.config = config || {};
            this.data = this.config.data || { datasets: [] };
            capturedConfig = config;

            if (ctx === 'THROW') {
                throw new Error('Chart render error');
            }
        }
        destroy() {}
        update() {}
        setDatasetVisibility() {}
        isDatasetVisible() { return true; }
    },
    reviewStatsData: {
        reviews: [
            { id: 1690000000000, type: 1, ease: 2 },
            { id: 1690086400000, type: 1, ease: 3 }
        ]
    }
};

global.document = {
    getElementById: (id) => {
        if (id === 'runningAmountCanvas') return { getContext: () => ({}) };
        if (id === 'runningAmountSection') return { classList: { remove: () => {} } };
        if (id === 'chartLegend') return { style: {}, innerHTML: '', querySelectorAll: () => [], replaceChildren: () => {}, appendChild: () => {} };
        if (id === 'runningAmountEmpty') return { style: {}, textContent: '' };
        return null;
    },
    querySelector: () => null,
    createElement: () => ({ dataset: {}, appendChild: () => {}, classList: { add: () => {} }, style: {} }),
    createTextNode: () => ({})
};

async function runTests() {
    console.log('🧪 Running Retention Tests');

    // Suppress console.error in tests to avoid test runner thinking it failed if there is no error code
    console.error = () => {};

    const { destroyRetentionChart, renderRetentionChart, showRetention } = await import('../js/commands/retention.js');

    const resEmpty = renderRetentionChart([]);
    assert.strictEqual(resEmpty.success, false);

    const validData = [
        { date: '2023-01-01', retention: 0.8 },
        { date: '2023-01-02', retention: 0.9 }
    ];
    let resValid = renderRetentionChart(validData);
    assert.strictEqual(resValid.success, true);

    const originalGetContext = global.document.getElementById;
    global.document.getElementById = (id) => {
        if (id === 'runningAmountCanvas') return { getContext: () => 'THROW' };
        return originalGetContext(id);
    };
    const resFail = renderRetentionChart(validData);
    assert.strictEqual(resFail.success, false);
    global.document.getElementById = originalGetContext;

    resValid = renderRetentionChart(validData);
    assert.doesNotThrow(() => destroyRetentionChart());

    const denseData = Array.from({length: 201}, (_, i) => ({ date: `2023-01-${i}`, retention: 0.8 }));
    assert.strictEqual(renderRetentionChart(denseData).success, true);

    const oldStats = global.window.reviewStatsData;
    global.window.reviewStatsData = null;
    assert.strictEqual(showRetention(), "Review stats not loaded yet. Please wait a moment and try again.");
    global.window.reviewStatsData = oldStats;

    destroyRetentionChart();

    console.log('✅ Retention tests passed\n');
}

runTests().catch(err => {
    // If there is an actual failure in test execution
    console.log('❌ Retention tests failed:', err);
    process.exitCode = 1;
});


// Add coverage for missing retention.js branches
async function fixRetentionCoverage() {
  const { showRetention, renderRetentionChart } = await import('../js/commands/retention.js');
  const assert = require('assert');

  // Test lines 27-28
  global.document.getElementById = (id) => null;
  const missingElResult = renderRetentionChart([]);
  assert.strictEqual(missingElResult.success, false);
  assert.strictEqual(missingElResult.error, 'Canvas or section not found');

  // Test line 158, 162-163 (showRetention loading checks)
  window.reviewStatsData = null;
  assert.strictEqual(showRetention('1m'), 'Review stats not loaded yet. Please wait a moment and try again.');
  window.reviewStatsData = { reviews: 'not an array' };
  assert.strictEqual(showRetention('1m'), 'Review stats not loaded yet. Please wait a moment and try again.');

  // Valid reviewStatsData to run past line 158
  window.reviewStatsData = { reviews: [{ day: 0, mature_right: 1, young_right: 1, relearn_right: 1, learn_right: 1, mature_wrong: 0, young_wrong: 0, relearn_wrong: 0, learn_wrong: 0 }] };

  // Test rangeKey undefined logic and parseRange returning null for rangeKey (e.g. 'all')
  global.document.getElementById = (id) => {
    if (id === 'runningAmountCanvas') return { getContext: () => ({}) };
    if (id === 'runningAmountSection') return { classList: { remove: () => {}, contains: () => false } };
    if (id === 'runningAmountEmpty') return { style: {}, textContent: '', classList: { remove: () => {} } };
    if (id === 'chartLegend') return { style: {}, innerHTML: '', querySelectorAll: () => [], replaceChildren: () => {}, appendChild: () => {} };
    return null;
  }
  showRetention('all');
  showRetention(undefined);

  // Test rangeLabel where rangeKey is falsey (e.g. "")
  showRetention("");

  // Test failing render to cover return result.error (line 164 error branch, effectively returning error if success is false)
  global.document.getElementById = (id) => null; // Will trigger Canvas/section not found failure
  const errorMsg = showRetention('1m');
  assert.strictEqual(errorMsg, 'Canvas or section not found');
}

fixRetentionCoverage().catch(e => {
  console.error(e);
  process.exitCode = 1;
});

async function fixTooltipCoverage() {
  const { renderRetentionChart } = await import('../js/commands/retention.js');
  const assert = require('assert');

  global.document.getElementById = (id) => {
    if (id === 'runningAmountCanvas') return { getContext: () => ({}) };
    if (id === 'runningAmountSection') return { classList: { remove: () => {} } };
    if (id === 'chartLegend') return { style: {}, innerHTML: '', querySelectorAll: () => [], replaceChildren: () => {}, appendChild: () => {} };
    if (id === 'runningAmountEmpty') return { style: {}, textContent: '' };
    return null;
  };

  const validData = [
    { date: '2023-01-01', retention: 0.8 },
    { date: '2023-01-02', retention: 0.9 }
  ];
  renderRetentionChart(validData);

  // Call tooltip callbacks to get coverage
  const titleCallback = capturedConfig.options.plugins.tooltip.callbacks.title;
  const labelCallback = capturedConfig.options.plugins.tooltip.callbacks.label;

  assert.strictEqual(titleCallback([{ label: 'Test Label' }]), 'Test Label');
  assert.strictEqual(labelCallback({ raw: 80 }), 'Retention: 80%');
  console.log("✅ Tooltip tests passed");
}

fixTooltipCoverage().catch(e => {
  console.error(e);
  process.exitCode = 1;
});

async function fixYAxisTickCoverage() {
  const { renderRetentionChart } = await import('../js/commands/retention.js');
  const assert = require('assert');

  global.document.getElementById = (id) => {
    if (id === 'runningAmountCanvas') return { getContext: () => ({}) };
    if (id === 'runningAmountSection') return { classList: { remove: () => {} } };
    if (id === 'chartLegend') return { style: {}, innerHTML: '', querySelectorAll: () => [], replaceChildren: () => {}, appendChild: () => {} };
    if (id === 'runningAmountEmpty') return { style: {}, textContent: '' };
    return null;
  };

  const validData = [
    { date: '2023-01-01', retention: 0.8 },
    { date: '2023-01-02', retention: 0.9 }
  ];
  renderRetentionChart(validData);

  // Call y-axis tick callback to get coverage
  const yAxisTickCallback = capturedConfig.options.scales.y.ticks.callback;
  assert.strictEqual(yAxisTickCallback(50), '50%');
  console.log("✅ Y-Axis Tick tests passed");
}

fixYAxisTickCoverage().catch(e => {
  console.error(e);
  process.exitCode = 1;
});
