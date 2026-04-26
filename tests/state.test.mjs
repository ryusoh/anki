import test from "node:test";
import assert from "node:assert";

// Mock window/document before dynamic import to avoid crash in config.js
global.window = { matchMedia: () => ({ matches: false }) };
global.document = { querySelector: () => null, createElement: () => ({}), head: { appendChild: () => {} } };

test("setActiveFilterTerm sets the filter term correctly", async () => {
  const { transactionState, setActiveFilterTerm, getActiveFilterTerm } = await import("../js/transactions/state.js");
  setActiveFilterTerm("test-term");
  assert.strictEqual(getActiveFilterTerm(), "test-term");
  setActiveFilterTerm(123); // Invalid type sets to empty
  assert.strictEqual(getActiveFilterTerm(), "");
});

test("resetSortState resets column and order to default", async () => {
  const { transactionState, resetSortState } = await import("../js/transactions/state.js");
  transactionState.sortState.column = "price";
  transactionState.sortState.order = "asc";
  resetSortState();
  assert.strictEqual(transactionState.sortState.column, "tradeDate");
  assert.strictEqual(transactionState.sortState.order, "desc");
});

test("transactionState array setters function correctly", async () => {
  const { transactionState, setAllTransactions, setFilteredTransactions, setSplitHistory, setRunningAmountSeries, setPortfolioSeries } = await import("../js/transactions/state.js");
  setAllTransactions([1]); assert.deepStrictEqual(transactionState.allTransactions, [1]);
  setAllTransactions("no"); assert.deepStrictEqual(transactionState.allTransactions, []);

  setFilteredTransactions([2]); assert.deepStrictEqual(transactionState.filteredTransactions, [2]);
  setFilteredTransactions("no"); assert.deepStrictEqual(transactionState.filteredTransactions, []);

  setSplitHistory([3]); assert.deepStrictEqual(transactionState.splitHistory, [3]);
  setSplitHistory("no"); assert.deepStrictEqual(transactionState.splitHistory, []);

  setRunningAmountSeries([4]); assert.deepStrictEqual(transactionState.runningAmountSeries, [4]);
  setRunningAmountSeries("no"); assert.deepStrictEqual(transactionState.runningAmountSeries, []);

  setPortfolioSeries([5]); assert.deepStrictEqual(transactionState.portfolioSeries, [5]);
  setPortfolioSeries("no"); assert.deepStrictEqual(transactionState.portfolioSeries, []);
});

test("transactionState map setters function correctly", async () => {
  const { transactionState, setRunningAmountSeriesMap, setPortfolioSeriesMap, setPerformanceSeries, setHistoricalPrices, setFxRatesByCurrency } = await import("../js/transactions/state.js");

  setRunningAmountSeriesMap({a:1}); assert.deepStrictEqual(transactionState.runningAmountSeriesByCurrency, {a:1});
  setRunningAmountSeriesMap("no"); assert.deepStrictEqual(transactionState.runningAmountSeriesByCurrency, {});

  setPortfolioSeriesMap({b:2}); assert.deepStrictEqual(transactionState.portfolioSeriesByCurrency, {b:2});
  setPortfolioSeriesMap("no"); assert.deepStrictEqual(transactionState.portfolioSeriesByCurrency, {});

  setPerformanceSeries({c:3}); assert.deepStrictEqual(transactionState.performanceSeries, {c:3});
  setPerformanceSeries("no"); assert.deepStrictEqual(transactionState.performanceSeries, {});

  setHistoricalPrices({d:4}); assert.deepStrictEqual(transactionState.historicalPrices, {d:4});
  setHistoricalPrices("no"); assert.deepStrictEqual(transactionState.historicalPrices, {});

  setFxRatesByCurrency({e:5}); assert.deepStrictEqual(transactionState.fxRatesByCurrency, {e:5});
  setFxRatesByCurrency("no"); assert.deepStrictEqual(transactionState.fxRatesByCurrency, {});
});

test("transactionState chart configuration updates correctly", async () => {
  const { transactionState, setChartVisibility, getChartVisibility, setShowChartLabels, getShowChartLabels, setActiveChart, setChartDateRange } = await import("../js/transactions/state.js");

  setChartVisibility("buy", false);
  assert.strictEqual(getChartVisibility().buy, false);

  setShowChartLabels(false);
  assert.strictEqual(getShowChartLabels(), false);
  setShowChartLabels(true);
  assert.strictEqual(getShowChartLabels(), true);

  setActiveChart("performance");
  assert.strictEqual(transactionState.activeChart, "performance");

  setChartDateRange({from: "a", to: "b"});
  assert.deepStrictEqual(transactionState.chartDateRange, {from: "a", to: "b"});
});

test("transactionState command history updates correctly", async () => {
  const { transactionState, pushCommandHistory, setHistoryIndex, resetHistoryIndex } = await import("../js/transactions/state.js");

  pushCommandHistory("cmd");
  assert.strictEqual(transactionState.commandHistory[0], "cmd");

  setHistoryIndex(1);
  assert.strictEqual(transactionState.historyIndex, 1);

  resetHistoryIndex();
  assert.strictEqual(transactionState.historyIndex, -1);
});

test("transactionState currency sets correctly", async () => {
  const { setSelectedCurrency, getSelectedCurrency } = await import("../js/transactions/state.js");

  setSelectedCurrency("EUR");
  assert.strictEqual(getSelectedCurrency(), "EUR");

  setSelectedCurrency(null);
  assert.strictEqual(getSelectedCurrency(), "EUR");
});

test("transactionState composition setters map arrays and filters", async () => {
  const { setCompositionFilterTickers, getCompositionFilterTickers, setCompositionAssetClassFilter, getCompositionAssetClassFilter } = await import("../js/transactions/state.js");

  setCompositionFilterTickers(["AAPL", "aapl ", null, "GOOG"]);
  assert.deepStrictEqual(getCompositionFilterTickers(), ["AAPL", "GOOG"]);

  setCompositionFilterTickers([]);
  assert.deepStrictEqual(getCompositionFilterTickers(), []);

  setCompositionAssetClassFilter("etf");
  assert.strictEqual(getCompositionAssetClassFilter(), "etf");

  setCompositionAssetClassFilter("invalid");
  assert.strictEqual(getCompositionAssetClassFilter(), null);
});

test("setZoomed properly sets internal zoom state", async () => {
  const { setZoomed, isZoomed } = await import("../js/transactions/state.js");
  setZoomed(true);
  assert.strictEqual(isZoomed(), true);
});
