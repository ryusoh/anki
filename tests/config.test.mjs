import test from "node:test";
import assert from "node:assert";
import {
  DATA_PATHS,
  TABLE_GLASS_EFFECT,
  GRAPH_BACKGROUND_IMAGE,
} from "../js/config.js";

test("DATA_PATHS exports valid data endpoints", () => {
  assert.strictEqual(typeof DATA_PATHS.customStats, "string");
  assert.strictEqual(typeof DATA_PATHS.reviewStats, "string");
  assert.strictEqual(typeof DATA_PATHS.graphData, "string");
});

test("glass effect configs have valid 3D properties", () => {
  assert.strictEqual(TABLE_GLASS_EFFECT.enabled, true);
  assert.strictEqual(TABLE_GLASS_EFFECT.excludeHeader, true);
  assert.strictEqual(
    typeof TABLE_GLASS_EFFECT.threeD.depth.desktop,
    "number",
  );
});

test("UI feature toggles have boolean flags", () => {
  assert.strictEqual(typeof GRAPH_BACKGROUND_IMAGE.enabled, "boolean");
});
