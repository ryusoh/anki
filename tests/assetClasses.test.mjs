import test from "node:test";
import assert from "node:assert";

// Mock window/document before dynamic import to avoid crash in config.js
global.window = { matchMedia: () => ({ matches: false }) };
global.document = { querySelector: () => null, createElement: () => ({}), head: { appendChild: () => {} } };

test("isLikelyFundTicker returns true for explicitly known ETFs", async () => {
  const { isLikelyFundTicker } = await import("../js/config/assetClasses.js");
  assert.strictEqual(isLikelyFundTicker("VTI"), true);
  assert.strictEqual(isLikelyFundTicker("VOO"), true);
  assert.strictEqual(isLikelyFundTicker("SPY"), true);
  assert.strictEqual(isLikelyFundTicker("QQQ"), true);
});

test("isLikelyFundTicker handles case insensitivity and whitespace", async () => {
  const { isLikelyFundTicker } = await import("../js/config/assetClasses.js");
  assert.strictEqual(isLikelyFundTicker("vti"), true);
  assert.strictEqual(isLikelyFundTicker("  VTI  "), true);
});

test("isLikelyFundTicker identifies mutual funds ending in X", async () => {
  const { isLikelyFundTicker } = await import("../js/config/assetClasses.js");
  assert.strictEqual(isLikelyFundTicker("VTSAX"), true);
  assert.strictEqual(isLikelyFundTicker("FNSFX"), true);
  assert.strictEqual(isLikelyFundTicker("PRUFX"), true); // Minimum 5 letters ending in X
});

test("isLikelyFundTicker returns false for common stocks and unknowns", async () => {
  const { isLikelyFundTicker } = await import("../js/config/assetClasses.js");
  assert.strictEqual(isLikelyFundTicker("AAPL"), false);
  assert.strictEqual(isLikelyFundTicker("GOOG"), false);
  assert.strictEqual(isLikelyFundTicker("RAND"), false); // 4 letters not ending in X
  assert.strictEqual(isLikelyFundTicker("XXX"), false); // Too short
});

test("isLikelyFundTicker returns false for invalid inputs", async () => {
  const { isLikelyFundTicker } = await import("../js/config/assetClasses.js");
  assert.strictEqual(isLikelyFundTicker(null), false);
  assert.strictEqual(isLikelyFundTicker(undefined), false);
  assert.strictEqual(isLikelyFundTicker(""), false);
  assert.strictEqual(isLikelyFundTicker("   "), false);
  assert.strictEqual(isLikelyFundTicker(123), false);
});
