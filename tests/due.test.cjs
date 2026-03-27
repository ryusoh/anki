const assert = require('assert');

global.window = {};
global.document = {
  getElementById: () => null,
  querySelector: () => null
};

async function runTests() {
  const { getFutureDueData } = await import('../js/commands/due.js');

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

  // Test without range restriction
  // Note: timeRange.js parses 'all' as null
  assert.deepStrictEqual(getFutureDueData('all'), [
    { day: 0, young: 10, mature: 5 },
    { day: 1, young: 5, mature: 10 },
    { day: 2, young: 2, mature: 15 }
  ]);

  // Test with range restriction (2 days = indices 0, 1)
  assert.deepStrictEqual(getFutureDueData('2d'), [
    { day: 0, young: 10, mature: 5 },
    { day: 1, young: 5, mature: 10 }
  ]);

  // Test with invalid range restriction that falls back to null/all
  assert.deepStrictEqual(getFutureDueData('invalid'), [
    { day: 0, young: 10, mature: 5 },
    { day: 1, young: 5, mature: 10 },
    { day: 2, young: 2, mature: 15 }
  ]);

  // Test byDeck without range restriction ('all')
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

  // Test byDeck with range restriction (2 days -> day < 2)
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

  // Test byDeck with empty structure
  window.customStatsData = {
    futureDueByDeck: {
      'Deck1': 'not_an_array'
    }
  };
  assert.deepStrictEqual(getFutureDueData('all', true), { 'Deck1': 'not_an_array' }); // The un-restricted getter returns allData directly which contains 'not_an_array'
  assert.deepStrictEqual(getFutureDueData('2d', true), {}); // Should ignore non-arrays when filtering with a range

  console.log('All tests passed.');
}

runTests().catch(e => {
  console.error(e);
  process.exitCode = 1;
});
