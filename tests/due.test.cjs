const assert = require('assert');

let capturedConfig = null;
global.window = {
  Chart: class {
    constructor(ctx, config) {
      this.config = config || {};
      this.data = this.config.data || { datasets: [] };
      capturedConfig = config;
      if (ctx === 'THROW') throw new Error('Chart render error');
    }
    destroy() {}
    update() {}
    setDatasetVisibility() {}
    isDatasetVisible() { return true; }
  }
};
global.document = {
  getElementById: () => null,
  querySelector: () => null
};

async function runTests() {
  const { getFutureDueData, showDue, renderFutureDueChart, destroyChart, getDueHelp } = await import('../js/commands/due.js');

  console.log('--- due.test.cjs ---');

  // Test when window.customStatsData is empty/undefined
  window.customStatsData = undefined;
  assert.deepStrictEqual(getFutureDueData(), []);
  assert.deepStrictEqual(getFutureDueData('1m', true), {});

  // Set up mock data
  window.customStatsData = {
    futureDue: [
      { day: 0, young: 10, mature: 5 },
      { day: 1, young: 5, mature: 10 },
      { day: 2, young: 2, mature: 15 }
    ],
    futureDueByDeck: {
      'Deck1': [
        { day: 0, young: 5, mature: 2 },
        { day: 1, young: 2, mature: 5 },
        { day: 2, young: 1, mature: 5 }
      ],
      'Deck2': [
        { day: 0, young: 5, mature: 3 },
        { day: 1, young: 3, mature: 5 },
        { day: 2, young: 1, mature: 10 }
      ]
    }
  };

  assert.deepStrictEqual(getFutureDueData('all'), [
    { day: 0, young: 10, mature: 5 },
    { day: 1, young: 5, mature: 10 },
    { day: 2, young: 2, mature: 15 }
  ]);

  assert.deepStrictEqual(getFutureDueData('2d'), [
    { day: 0, young: 10, mature: 5 },
    { day: 1, young: 5, mature: 10 }
  ]);

  assert.deepStrictEqual(getFutureDueData('invalid'), [
    { day: 0, young: 10, mature: 5 },
    { day: 1, young: 5, mature: 10 },
    { day: 2, young: 2, mature: 15 }
  ]);

  assert.deepStrictEqual(getFutureDueData('all', true), {
    'Deck1': [
      { day: 0, young: 5, mature: 2 },
      { day: 1, young: 2, mature: 5 },
      { day: 2, young: 1, mature: 5 }
    ],
    'Deck2': [
      { day: 0, young: 5, mature: 3 },
      { day: 1, young: 3, mature: 5 },
      { day: 2, young: 1, mature: 10 }
    ]
  });

  assert.deepStrictEqual(getFutureDueData('2d', true), {
    'Deck1': [
      { day: 0, young: 5, mature: 2 },
      { day: 1, young: 2, mature: 5 }
    ],
    'Deck2': [
      { day: 0, young: 5, mature: 3 },
      { day: 1, young: 3, mature: 5 }
    ]
  });

  window.customStatsData = {
    futureDueByDeck: {
      'Deck1': 'not_an_array'
    }
  };
  assert.deepStrictEqual(getFutureDueData('all', true), { 'Deck1': 'not_an_array' });
  assert.deepStrictEqual(getFutureDueData('2d', true), {});

  // --- Extended Coverage for showDue & renderFutureDueChart ---

  const originalGetElementById = global.document.getElementById;
  global.document.getElementById = (id) => {
    if (id === 'runningAmountCanvas') return { getContext: () => ({}) };
    if (id === 'runningAmountSection') return { classList: { remove: () => {}, contains: () => false } };
    if (id === 'chartLegend') return { style: {}, innerHTML: '', querySelectorAll: () => [] };
    if (id === 'runningAmountEmpty') return { style: {}, textContent: '', classList: { remove: () => {} } };
    return null;
  };

  // Ensure DOM is ready for showDue by re-applying the mock globally
  window.customStatsData = {
    futureDue: [
      { day: 0, young: 10, mature: 5 },
      { day: 1, young: 5, mature: 10 },
      { day: 2, young: 2, mature: 15 }
    ],
    futureDueByDeck: {
      'Deck1': [
        { day: 0, young: 5, mature: 2 },
        { day: 1, young: 2, mature: 5 },
        { day: 2, young: 1, mature: 5 }
      ]
    }
  };

  // In `js/commands/due.js`, `const Chart = window.Chart;` evaluates once.
  // Because my initial mock set `window` to `{}`, `window.Chart` was undefined!
  // I already updated the top of this script to initialize `window.Chart` *before* the import.

  // Test showDue
  assert.strictEqual(showDue('2d'), "Rendered upcoming reviews chart (2 days).");
  assert.strictEqual(showDue('all'), "Rendered upcoming reviews chart (all time).");

  // Setup full valid customStatsData for reviews.js `groupAndSortDecks`
  window.customStatsData.decks = [{name: 'Deck1', total: 100}];
  window.customStatsData.groups = [];

  assert.strictEqual(showDue('all', true), "Rendered upcoming reviews chart (all time).");

  // Wait for the async renderFutureDueChart(byDeck=true) logic to finish execution.
  await new Promise(resolve => setTimeout(resolve, 50));

  // Test render error
  global.document.getElementById = (id) => {
    if (id === 'runningAmountCanvas') return { getContext: () => 'THROW' };
    return originalGetElementById(id);
  };
  assert.strictEqual(renderFutureDueChart(window.customStatsData.futureDue).success, false);
  global.document.getElementById = originalGetElementById;

  // Test missing elements again
  global.document.getElementById = (id) => null;
  assert.strictEqual(renderFutureDueChart([]).success, false);
  global.document.getElementById = originalGetElementById;

  // Test destroy
  assert.doesNotThrow(() => destroyChart());

  // Test help
  assert.strictEqual(Array.isArray(getDueHelp()), true);

  // Test callbacks (for coverage)
  renderFutureDueChart(window.customStatsData.futureDue);
  if (capturedConfig && capturedConfig.options && capturedConfig.options.plugins && capturedConfig.options.plugins.tooltip) {
    const titleCallback = capturedConfig.options.plugins.tooltip.callbacks.title;
    assert.strictEqual(titleCallback([{label: "Title"}]), "Title");

    const labelCallback = capturedConfig.options.plugins.tooltip.callbacks.label;
    assert.strictEqual(labelCallback({raw: 10, dataset: {label: "Young"}}), "Young: 10");
    assert.strictEqual(labelCallback({raw: 0, dataset: {label: "Young"}}), null);

    const byDeckCallback = capturedConfig.options.plugins.tooltip.callbacks.label;
    // We can just call it directly to hit branches
    assert.strictEqual(byDeckCallback({raw: 5, dataset: {label: "Deck1"}}), "Deck1: 5");
  }

  // Cover empty state
  window.customStatsData.futureDue = [];
  assert.strictEqual(renderFutureDueChart(window.customStatsData.futureDue).success, false);

  // Cover byDeck branch fully
  const longData = Array.from({length: 150}, (_, i) => ({ day: i, young: 1, mature: 1 }));
  renderFutureDueChart(longData);

  console.log('All tests passed.');
}

runTests().catch(e => {
  console.error(e);
  process.exitCode = 1;
});
