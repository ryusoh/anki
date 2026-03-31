import assert from "assert";
import { toggleZoom, getZoomState } from "../js/commands/zoom.js";

function setupDOM(hasElements = true, hasChart = true, isChartHidden = false) {
  const document = {
    getElementById: (id) => {
      if (!hasElements) return null;
      if (id === "terminal") {
        return {
          id: "terminal",
          getBoundingClientRect: () => ({ top: 0, bottom: 500, height: 500 }),
          classList: { add: () => {}, remove: () => {} },
        };
      }
      if (id === "runningAmountSection") {
        if (!hasChart) return null;
        return {
          id: "runningAmountSection",
          getBoundingClientRect: () => ({ bottom: 600 }),
          classList: {
            add: () => {},
            remove: () => {},
            contains: (c) => (c === "is-hidden" ? isChartHidden : false),
          },
        };
      }
      if (id === "terminalOutput") {
        return {
          id: "terminalOutput",
          getBoundingClientRect: () => ({ height: 270 }),
          dataset: {},
        };
      }
      return null;
    },
  };
  global.document = document;

  global.gsap = {
    timeline: (opts) => {
      return {
        to: (el, config, offset) => {},
        play: () => {
          if (opts && opts.onComplete) opts.onComplete();
        },
      };
    },
    set: () => {},
  };

  // Override gsap timeline slightly to trigger onComplete synchronously
  const originalTimeline = global.gsap.timeline;
  global.gsap.timeline = (opts) => {
    const tl = originalTimeline(opts);
    // We need the animation to "complete" to resolve the promises
    setTimeout(() => {
      if (opts && opts.onComplete) opts.onComplete();
    }, 0);
    return tl;
  };
}

async function runTests() {
  console.log("🧪 Running Zoom Tests");

  // Test 1: Missing elements
  setupDOM(false);
  let result = await toggleZoom();
  assert.strictEqual(result.zoomed, false);
  assert.strictEqual(
    result.message,
    "Unable to toggle zoom: terminal elements not found.",
  );

  // Test 2: Zoom in with chart visible
  setupDOM(true, true, false);
  // ensure initially false
  // we need to actually await toggleZoom properly
  // Wait, the zoomed state is module scoped. We can just test getZoomState

  // Zoom in
  result = await toggleZoom();
  assert.strictEqual(result.zoomed, true);
  assert.strictEqual(result.message, "Terminal zoomed in.");
  assert.strictEqual(getZoomState(), true);

  // Test 3: Zoom out
  result = await toggleZoom();
  assert.strictEqual(result.zoomed, false);
  assert.strictEqual(result.message, "Terminal zoomed out.");
  assert.strictEqual(getZoomState(), false);

  // Test 4: Zoom in with chart hidden
  setupDOM(true, true, true);
  result = await toggleZoom();
  assert.strictEqual(result.zoomed, true);

  // Zoom out to reset
  await toggleZoom();

  // Test 5: Zoom in without chart element
  setupDOM(true, false, false);
  result = await toggleZoom();
  assert.strictEqual(result.zoomed, true);

  console.log("✅ Zoom tests passed\n");
}

runTests().catch((err) => {
  console.error("❌ Zoom tests failed:", err);
  process.exit(1);
});
