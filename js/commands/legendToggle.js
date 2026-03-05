/**
 * Legend Toggle Utility
 * Wires click-to-toggle on bottom custom legend items.
 * Clicking a legend item hides/shows the corresponding chart dataset
 * with Chart.js's built-in animation.
 *
 * Usage:
 *   import { bindLegendToggle } from "@js/commands/legendToggle.js";
 *   const chart = new Chart(ctx, config);
 *   bindLegendToggle(chart, legendEl);
 */

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
    items.forEach((item) => {
        item.addEventListener("click", () => {
            const index = parseInt(item.dataset.datasetIndex, 10);
            if (isNaN(index)) return;

            const meta = chart.getDatasetMeta(index);
            meta.hidden = !meta.hidden;
            item.classList.toggle("legend-disabled", meta.hidden);
            chart.update("active"); // animated transition
        });
    });
}
