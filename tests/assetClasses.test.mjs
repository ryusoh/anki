import test from "node:test";
import assert from "node:assert";
import { isLikelyFundTicker } from "../js/config/assetClasses.js";

test("isLikelyFundTicker handles invalid inputs", () => {
  assert.strictEqual(isLikelyFundTicker(null), false);
  assert.strictEqual(isLikelyFundTicker(undefined), false);
  assert.strictEqual(isLikelyFundTicker(123), false);
  assert.strictEqual(isLikelyFundTicker({}), false);
  assert.strictEqual(isLikelyFundTicker([]), false);
});

test("isLikelyFundTicker handles empty or whitespace strings", () => {
  assert.strictEqual(isLikelyFundTicker(""), false);
  assert.strictEqual(isLikelyFundTicker("   "), false);
  assert.strictEqual(isLikelyFundTicker("\t\n"), false);
});

test("isLikelyFundTicker recognizes known overrides", () => {
  assert.strictEqual(isLikelyFundTicker("VT"), true);
  assert.strictEqual(isLikelyFundTicker("vt"), true); // case insensitive
  assert.strictEqual(isLikelyFundTicker(" VOO "), true); // trims whitespace
  assert.strictEqual(isLikelyFundTicker("QQQ"), true);
  assert.strictEqual(isLikelyFundTicker("BNDW"), true);
});

test("isLikelyFundTicker recognizes mutual funds ending in X", () => {
  assert.strictEqual(isLikelyFundTicker("VTSAX"), true);
  assert.strictEqual(isLikelyFundTicker("vtsax"), true);
  assert.strictEqual(isLikelyFundTicker("SWPPX"), true); // not in overrides, but length 5 and ends in X
  assert.strictEqual(isLikelyFundTicker("VFIAX"), true);
});

test("isLikelyFundTicker rejects non-funds", () => {
  assert.strictEqual(isLikelyFundTicker("AAPL"), false);
  assert.strictEqual(isLikelyFundTicker("MSFT"), false);
  assert.strictEqual(isLikelyFundTicker("TSLA"), false);
  assert.strictEqual(isLikelyFundTicker("BRK.B"), false);

  // Rejects shorter tickers ending in X
  assert.strictEqual(isLikelyFundTicker("USX"), false); // length 3
  assert.strictEqual(isLikelyFundTicker("XYZX"), false); // length 4
});
