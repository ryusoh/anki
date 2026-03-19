/**
 * Legend Toggle Utility
 * Wires click-to-toggle on bottom custom legend items.
 * Clicking a legend item hides/shows the corresponding chart dataset
 * with Chart.js's built-in animation.
 *
 * Usage:
 *   import { bindLegendToggle } from "#js/commands/legendToggle.js";
 *   const chart = new Chart(ctx, config);
 *   bindLegendToggle(chart, legendEl);
 */

// Persistent state for hidden dataset labels
const hiddenLabels = new Set();

/**
 * Check if a label is currently hidden in the global legend state.
 * @param {string} label
 * @returns {boolean}
 */
export function isLabelHidden(label) {
  return hiddenLabels.has(label);
}

/**
 * Bind click handlers on legend items to toggle dataset visibility.
 *
 * Each clickable legend item must have a `data-dataset-index` attribute
 * matching the dataset index in the chart.
 *
 * @param {Chart} chart - Chart.js instance
 * @param {HTMLElement} legendEl - The legend container element
 */
export function bindLegendToggle(chart, legendEl) {
  if (!chart || !legendEl) return;

  const items = legendEl.querySelectorAll("[data-dataset-index]");

  // 1. Setup accessibility attributes
  items.forEach((item) => {
    item.setAttribute("role", "button");
    item.setAttribute("tabindex", "0");
    item.setAttribute("aria-pressed", "true");
  });

  // 2. Initial sync: Apply any previously hidden labels from our global state
  chart.data.datasets.forEach((dataset, index) => {
    if (hiddenLabels.has(dataset.label)) {
      const meta = chart.getDatasetMeta(index);
      meta.hidden = true;

      // Find corresponding legend item and add disabled class
      const item = Array.from(items).find(
        (i) => parseInt(i.dataset.datasetIndex, 10) === index,
      );
      if (item) {
        item.classList.add("legend-disabled");
        item.setAttribute("aria-pressed", "false");
      }
    }
  });

  // Trigger update if we modified any visibility (no animation for initial sync)
  chart.update("none");

  // 3. Click handlers: Toggle visibility and update global state
  items.forEach((item) => {
    const toggleLegend = () => {
      const index = parseInt(item.dataset.datasetIndex, 10);
      if (isNaN(index)) return;

      const dataset = chart.data.datasets[index];
      const meta = chart.getDatasetMeta(index);

      // Toggle state
      meta.hidden = !meta.hidden;
      item.classList.toggle("legend-disabled", meta.hidden);
      item.setAttribute("aria-pressed", (!meta.hidden).toString());

      // Persist by label name
      if (meta.hidden) {
        if (dataset.label) hiddenLabels.add(dataset.label);
      } else {
        if (dataset.label) hiddenLabels.delete(dataset.label);
      }

      chart.update(); // animated transition
    };

    item.addEventListener("click", toggleLegend);
    item.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggleLegend();
      }
    });
  });
}
