import { describe, it, expect, beforeEach } from "@jest/globals";
import { JSDOM } from "jsdom";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const d3Code = fs.readFileSync(
  path.join(__dirname, "../web/d3.min.js"),
  "utf8",
);
const rhCode = fs.readFileSync(
  path.join(__dirname, "../web/anki-review-heatmap.js"),
  "utf8",
);

describe("Heatmap hover tooltip HTML tags", () => {
  let dom;
  let window;
  let document;

  beforeEach(() => {
    dom = new JSDOM(
      `<!DOCTYPE html>
      <html>
        <head>
          <style></style>
        </head>
        <body>
          <div class="rh-container rh-view-overview">
            <div class="heatmap">
              <div id="cal-heatmap"></div>
            </div>
          </div>
        </body>
      </html>`,
      {
        url: "http://127.0.0.1:8080/",
        runScripts: "outside-only",
      },
    );
    window = dom.window;
    document = window.document;

    // Mock globals required by the scripts
    window.pycmd = () => {};

    // Load D3 and Review Heatmap JS
    window.eval(d3Code);
    window.eval(rhCode);
  });

  afterEach(() => {
    if (dom) {
      dom.window.close();
    }
  });

  it("should render formatted bold tags as HTML rather than raw text", () => {
    // 2023-01-15 12:00:00 UTC (1673784000 seconds)
    const today = new Date(Date.UTC(2023, 0, 15, 12, 0, 0));
    const start = new Date(Date.UTC(2023, 0, 1, 0, 0, 0));
    const stop = new Date(Date.UTC(2023, 0, 31, 23, 59, 59));

    const options = {
      domain: "month",
      subdomain: "day",
      range: 1,
      domLabForm: "%b",
      start: start.getTime(),
      stop: stop.getTime(),
      today: today.getTime(),
      offset: 0,
      legend: [1, 2, 3, 4],
      whole: true,
      cell_shape: "rectangle",
    };

    const reviewHeatmap = new window.ReviewHeatmap(options);

    // We add 5 reviews on 2023-01-15
    const activeTimestamp = Math.floor(today.getTime() / 1000);
    const data = {
      [activeTimestamp]: 5,
    };

    reviewHeatmap.create(data);

    // Find the subdomain cells (usually <rect class="graph-rect ..."> or similar)
    const rects = document.querySelectorAll(".graph-rect");
    expect(rects.length).toBeGreaterThan(0);

    // Get the first rect and dispatch mouseover
    const cell = rects[0];
    const mouseOverEvent = new window.MouseEvent("mouseover", {
      bubbles: true,
      cancelable: true,
    });
    cell.dispatchEvent(mouseOverEvent);

    // Find the tooltip element
    const tooltip = document.querySelector(".ch-tooltip");
    expect(tooltip).not.toBeNull();

    // Verify it is displayed
    expect(tooltip.style.display).not.toBe("none");

    // The tooltip should parse the <b> tags, meaning we should find actual <b> elements
    const boldElements = tooltip.querySelectorAll("b");
    expect(boldElements.length).toBeGreaterThan(0);
    expect(tooltip.innerHTML).toContain("<b>");
  });
});
