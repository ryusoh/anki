import assert from 'assert';

global.document = {
  querySelector: () => null
};
global.window = {
  innerWidth: 1024,
  location: { search: '' },
  localStorage: { getItem: () => null, setItem: () => {} }
};

async function runTests() {
  const {
    transactionState,
    setActiveFilterTerm,
    getActiveFilterTerm,
    resetSortState,
    setAllTransactions,
    setFilteredTransactions,
    setSplitHistory,
    setRunningAmountSeries,
    setRunningAmountSeriesMap,
    setPortfolioSeries,
    setPortfolioSeriesMap,
    setPerformanceSeries,
    setChartVisibility,
    getChartVisibility,
    setShowChartLabels,
    getShowChartLabels,
    pushCommandHistory,
    resetHistoryIndex,
    setHistoryIndex,
    setActiveChart,
    setHistoricalPrices,
    setChartDateRange,
    setSelectedCurrency,
    getSelectedCurrency,
    setFxRatesByCurrency,
    setCompositionFilterTickers,
    getCompositionFilterTickers,
    setCompositionAssetClassFilter,
    getCompositionAssetClassFilter,
    setZoomed,
    isZoomed
  } = await import('../js/transactions/state.js');

  console.log('--- state.test.js ---');

  // Test: setActiveFilterTerm / getActiveFilterTerm
  setActiveFilterTerm(' AAPL ');
  assert.strictEqual(getActiveFilterTerm(), 'AAPL', 'setActiveFilterTerm should trim whitespace');
  setActiveFilterTerm(123);
  assert.strictEqual(getActiveFilterTerm(), '', 'setActiveFilterTerm should handle non-strings');

  // Test: resetSortState
  transactionState.sortState.column = 'amount';
  transactionState.sortState.order = 'asc';
  resetSortState();
  assert.strictEqual(transactionState.sortState.column, 'tradeDate');
  assert.strictEqual(transactionState.sortState.order, 'desc');

  // Test: array setters
  setAllTransactions([{ id: 1 }]);
  assert.deepStrictEqual(transactionState.allTransactions, [{ id: 1 }]);
  setAllTransactions('not array');
  assert.deepStrictEqual(transactionState.allTransactions, []);

  setFilteredTransactions([{ id: 2 }]);
  assert.deepStrictEqual(transactionState.filteredTransactions, [{ id: 2 }]);
  setFilteredTransactions('not array');
  assert.deepStrictEqual(transactionState.filteredTransactions, []);

  setSplitHistory([{ split: 2 }]);
  assert.deepStrictEqual(transactionState.splitHistory, [{ split: 2 }]);
  setSplitHistory(null);
  assert.deepStrictEqual(transactionState.splitHistory, []);

  setRunningAmountSeries([1, 2, 3]);
  assert.deepStrictEqual(transactionState.runningAmountSeries, [1, 2, 3]);
  setRunningAmountSeries(123);
  assert.deepStrictEqual(transactionState.runningAmountSeries, []);

  setPortfolioSeries([4, 5, 6]);
  assert.deepStrictEqual(transactionState.portfolioSeries, [4, 5, 6]);
  setPortfolioSeries(123);
  assert.deepStrictEqual(transactionState.portfolioSeries, []);

  // Test: object map setters
  setRunningAmountSeriesMap({ USD: [1] });
  assert.deepStrictEqual(transactionState.runningAmountSeriesByCurrency, { USD: [1] });
  setRunningAmountSeriesMap(null);
  assert.deepStrictEqual(transactionState.runningAmountSeriesByCurrency, {});

  setPortfolioSeriesMap({ EUR: [2] });
  assert.deepStrictEqual(transactionState.portfolioSeriesByCurrency, { EUR: [2] });
  setPortfolioSeriesMap(null);
  assert.deepStrictEqual(transactionState.portfolioSeriesByCurrency, {});

  setPerformanceSeries({ AAPL: [3] });
  assert.deepStrictEqual(transactionState.performanceSeries, { AAPL: [3] });
  setPerformanceSeries(null);
  assert.deepStrictEqual(transactionState.performanceSeries, {});

  setHistoricalPrices({ AAPL: 150 });
  assert.deepStrictEqual(transactionState.historicalPrices, { AAPL: 150 });
  setHistoricalPrices(null);
  assert.deepStrictEqual(transactionState.historicalPrices, {});

  setFxRatesByCurrency({ EUR: { rate: 1.1 } });
  assert.deepStrictEqual(transactionState.fxRatesByCurrency, { EUR: { rate: 1.1 } });
  setFxRatesByCurrency(null);
  assert.deepStrictEqual(transactionState.fxRatesByCurrency, {});

  // Test: chart visibility
  setChartVisibility('contribution', false);
  assert.strictEqual(getChartVisibility().contribution, false);
  setChartVisibility('buy', true);
  assert.strictEqual(getChartVisibility().buy, true);

  // Test: chart labels
  setShowChartLabels(false);
  assert.strictEqual(getShowChartLabels(), false);
  setShowChartLabels(true);
  assert.strictEqual(getShowChartLabels(), true);

  // Test: command history
  pushCommandHistory('test1');
  pushCommandHistory('test2');
  assert.strictEqual(transactionState.commandHistory[0], 'test2');
  assert.strictEqual(transactionState.commandHistory[1], 'test1');

  // Test: history index
  setHistoryIndex(5);
  assert.strictEqual(transactionState.historyIndex, 5);
  resetHistoryIndex();
  assert.strictEqual(transactionState.historyIndex, -1);

  // Test: active chart
  setActiveChart('performance');
  assert.strictEqual(transactionState.activeChart, 'performance');

  // Test: chart date range
  setChartDateRange({ from: '2023-01-01', to: '2023-12-31' });
  assert.deepStrictEqual(transactionState.chartDateRange, { from: '2023-01-01', to: '2023-12-31' });

  // Test: currency
  setSelectedCurrency('EUR');
  assert.strictEqual(getSelectedCurrency(), 'EUR');
  // Just test that transactionState.selectedCurrency changed
  assert.strictEqual(transactionState.selectedCurrency, 'EUR');
  setSelectedCurrency('');
  assert.strictEqual(getSelectedCurrency(), 'EUR'); // Should not change if invalid

  // Test: composition filters
  setCompositionFilterTickers([' aapl ', 'MSFT', 'aapl']);
  assert.deepStrictEqual(getCompositionFilterTickers(), ['AAPL', 'MSFT']);
  setCompositionFilterTickers([]);
  assert.deepStrictEqual(getCompositionFilterTickers(), []);
  setCompositionFilterTickers([123]);
  assert.deepStrictEqual(getCompositionFilterTickers(), []);

  setCompositionAssetClassFilter('etf');
  assert.strictEqual(getCompositionAssetClassFilter(), 'etf');
  setCompositionAssetClassFilter('invalid');
  assert.strictEqual(getCompositionAssetClassFilter(), null);

  // Test: zoom
  setZoomed(true);
  assert.strictEqual(isZoomed(), true);
  setZoomed(false);
  assert.strictEqual(isZoomed(), false);

  delete global.document;
  delete global.window;
  console.log('All tests passed.');
}

runTests().catch(e => {
  console.error(e);
  process.exitCode = 1;
});
