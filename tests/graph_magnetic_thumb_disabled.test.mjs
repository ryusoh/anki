import test from "node:test";
import assert from "node:assert";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const src = fs.readFileSync(
  path.join(__dirname, "..", "js", "graph", "graph.js"),
  "utf8",
);

// ---------------------------------------------------------------------------
// The magnetic cursor-pull effect on the timeline slider thumb is disabled:
// no GSAP tweens may target the thumb, and no pointer listeners may be
// attached to the slider group. The thumb must still track the slider value
// (updateTimeline sets its `left` from the slider position).
// ---------------------------------------------------------------------------

test("no gsap quickTo tweens target the magnetic thumb", () => {
  assert.strictEqual(
    [...src.matchAll(/quickTo\(\s*magThumb/g)].length,
    0,
    "graph.js still pre-allocates gsap quickTo tweens for the magnetic thumb",
  );
});

test("no pointer listeners are attached to the slider group", () => {
  assert.strictEqual(
    [...src.matchAll(/sliderGroup\.addEventListener/g)].length,
    0,
    "graph.js still attaches mouse listeners to #slider-group for the magnetic pull",
  );
});

test("no gsap tween resets the thumb transform on mouseleave", () => {
  assert.strictEqual(
    [...src.matchAll(/gsap\.to\(\s*magThumb/g)].length,
    0,
    "graph.js still has the elastic snap-back tween on the magnetic thumb",
  );
});

test("thumb still tracks the slider value in updateTimeline", () => {
  assert.match(
    src,
    /magThumb\.style\.left/,
    "the slider-position sync for #magnetic-thumb must be kept",
  );
});
