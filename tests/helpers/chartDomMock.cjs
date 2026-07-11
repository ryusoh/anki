/**
 * Shared DOM/Chart mocks for testing js/commands/{due,reviews,retention}.js.
 * Those modules all target the same #runningAmountCanvas / #runningAmountSection
 * / #chartLegend / #runningAmountEmpty elements and construct `window.Chart`.
 * Extracted from copy-pasted mocks in due_calendar.test.cjs and
 * retention_calendar.test.cjs (2026-07-11) so future command tests don't
 * re-derive this boilerplate by reading multiple existing test files.
 *
 * Not a fit for every test in tests/: handler-level tests that exercise
 * scroll/zoom/dataset attributes (see handler_regression_extra.test.cjs,
 * handler_calendar.test.cjs) use a broader one-size-fits-all element mock
 * instead -- that is a deliberate, different idiom, not something to unify
 * with this one.
 */

function createChartDomMock() {
  return {
    createTextNode: (text) => ({ nodeType: 3, textContent: text }),
    createElement: () => ({
      setAttribute: () => {},
      appendChild: () => {},
      style: {},
      classList: { add: () => {}, remove: () => {}, contains: () => false },
    }),
    getElementById: (id) => {
      if (id === "runningAmountCanvas") return { getContext: () => ({}) };
      if (id === "runningAmountSection")
        return { classList: { remove: () => {}, contains: () => false } };
      if (id === "chartLegend")
        return {
          style: {},
          textContent: "",
          appendChild: () => {},
          replaceChildren: () => {},
          innerHTML: "",
          querySelectorAll: () => [],
        };
      if (id === "runningAmountEmpty")
        return {
          style: {},
          textContent: "",
          classList: { remove: () => {} },
        };
      return null;
    },
    querySelector: () => null,
  };
}

/**
 * A minimal `window.Chart` stub. Records the most recent constructor config
 * so tests can assert on labels/datasets without a real Chart.js/canvas.
 * @returns {{MockChart: Function, getLastConfig: () => object|null}}
 */
function createMockChartClass() {
  let lastConfig = null;
  class MockChart {
    constructor(ctx, config) {
      this.config = config || {};
      this.data = this.config.data || { datasets: [] };
      lastConfig = config;
      if (ctx === "THROW") throw new Error("Chart render error");
    }
    destroy() {}
    update() {}
    setDatasetVisibility() {}
    isDatasetVisible() {
      return true;
    }
  }
  return { MockChart, getLastConfig: () => lastConfig };
}

module.exports = { createChartDomMock, createMockChartClass };
