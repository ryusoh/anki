import assert from 'assert';

// Mock global objects
global.document = {
  querySelector: () => null
};
global.window = {
  innerWidth: 1024,
  location: { search: '' },
  localStorage: { getItem: () => null, setItem: () => {} }
};

// Now we can import dynamically
async function runTests() {
  const { formatDate, escapeHtml, parseCSVLine, formatCurrencyCompact, formatCurrency, formatCurrencyInlineValue, convertValueToCurrency, convertBetweenCurrencies } = await import('../js/transactions/utils.js');
  const { setSelectedCurrency, setFxRatesByCurrency, transactionState } = await import('../js/transactions/state.js');

  console.log('--- utils_format.test.js ---');

  // Test: formatDate
  assert.strictEqual(formatDate('2023-01-05T12:00:00Z'), '2023-01-05', 'formatDate should format ISO string correctly');
  assert.strictEqual(formatDate(new Date('2023-01-05T12:00:00Z')), '2023-01-05', 'formatDate should format Date correctly');

  // Test: escapeHtml
  assert.strictEqual(escapeHtml('<script>alert("1")</script>&\''), '&lt;script&gt;alert(&quot;1&quot;)&lt;/script&gt;&amp;&#039;', 'escapeHtml should escape all special characters');
  assert.strictEqual(escapeHtml(123), 123, 'escapeHtml should return non-strings unchanged');

  // Test: parseCSVLine
  assert.deepStrictEqual(parseCSVLine('1,2,3'), ['1', '2', '3'], 'parseCSVLine should split by comma');
  assert.deepStrictEqual(parseCSVLine('1,"2,3",4'), ['1', '2,3', '4'], 'parseCSVLine should handle quotes');
  assert.deepStrictEqual(parseCSVLine('1,"2,""3""",4'), ['1', '2,"3"', '4'], 'parseCSVLine should handle escaped quotes');

  // Test: formatCurrencyCompact
  setSelectedCurrency('USD');
  assert.strictEqual(formatCurrencyCompact(1500), '$1.5k');
  assert.strictEqual(formatCurrencyCompact(1500000), '$1.50M');
  assert.strictEqual(formatCurrencyCompact(1000000), '$1M');
  assert.strictEqual(formatCurrencyCompact(1000000000), '$1B');
  assert.strictEqual(formatCurrencyCompact(1500000000), '$1.50B');
  assert.strictEqual(formatCurrencyCompact(1000000000000), '$1T');
  assert.strictEqual(formatCurrencyCompact(1500000000000), '$1.50T');
  assert.strictEqual(formatCurrencyCompact(0.001), '$0');
  assert.strictEqual(formatCurrencyCompact(-1500), '-$1.5k');
  assert.strictEqual(formatCurrencyCompact('abc'), '$0');

  assert.strictEqual(formatCurrencyCompact(10000000000000), '$10T');
  assert.strictEqual(formatCurrencyCompact(100000000000000), '$100T');
  assert.strictEqual(formatCurrencyCompact(10000000000), '$10B');
  assert.strictEqual(formatCurrencyCompact(100000000000), '$100B');
  assert.strictEqual(formatCurrencyCompact(10000000), '$10M');
  assert.strictEqual(formatCurrencyCompact(100000000), '$100M');
  assert.strictEqual(formatCurrencyCompact(10000), '$10k');
  assert.strictEqual(formatCurrencyCompact(100000), '$100k');

  // Custom non-integer edge cases for non-CJK
  assert.strictEqual(formatCurrencyCompact(10), '$10');

  // formatCurrency / formatCurrencyInlineValue
  setSelectedCurrency('USD');
  assert.strictEqual(formatCurrency(1500), '$1,500.00');
  assert.strictEqual(formatCurrency(-1500), '-$1,500.00');
  assert.strictEqual(formatCurrency('abc'), '$0.00');
  assert.strictEqual(formatCurrencyInlineValue(1500.5), '$1,501');
  assert.strictEqual(formatCurrencyInlineValue(1500.5, { digits: 2 }), '$1,500.50');
  assert.strictEqual(formatCurrencyInlineValue('abc', { digits: 2 }), '$0.00');

  // test convertValueToCurrency
  assert.strictEqual(convertValueToCurrency('abc', '2023-01-01', 'USD'), 0);
  assert.strictEqual(convertValueToCurrency(100, '2023-01-01', 'USD'), 100);

  // mock fxRates
  setFxRatesByCurrency({
    EUR: {
      map: new Map([['2023-01-01', 0.9], ['2023-01-05', 0.85]]),
      sorted: [
        { date: '2023-01-01', ts: Date.parse('2023-01-01') },
        { date: '2023-01-05', ts: Date.parse('2023-01-05') }
      ]
    }
  });

  assert.strictEqual(convertValueToCurrency(100, '2023-01-01', 'EUR'), 90);
  assert.strictEqual(convertValueToCurrency(100, '2023-01-05', 'EUR'), 85);
  // binary search in findFxRate returns nearest index. '2023-01-03' is larger than '2023-01-01'
  assert.strictEqual(convertValueToCurrency(100, '2023-01-03', 'EUR'), 90); // Should pick the closest before or after logic. Let's trace findFxRate

  assert.strictEqual(convertBetweenCurrencies(100, 'EUR', '2023-01-01', 'USD'), 100 / 0.9);
  assert.strictEqual(convertBetweenCurrencies(100, 'USD', '2023-01-01', 'EUR'), 100 * 0.9);
  assert.strictEqual(convertBetweenCurrencies(100, 'EUR', '2023-01-01', 'EUR'), 100);

  // Some invalid rates checks
  assert.strictEqual(convertBetweenCurrencies(100, 'EUR', '1999-01-01', 'USD'), 100 / 0.9);

  // Teardown globals
  delete global.document;
  delete global.window;

  console.log('All tests passed.');
}

runTests().catch(e => {
  console.error(e);
  process.exitCode = 1;
});
