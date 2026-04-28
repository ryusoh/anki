import test from "node:test";
import assert from "node:assert";

test("getBaseUrl uses location correctly", async () => {
  // Create mock environment
  global.window = { innerWidth: 1024 };
  global.document = { querySelector: () => null };

  const { getBaseUrl, getHoldingAssetClass } = await import("../js/config.js");

  // Test getBaseUrl
  assert.strictEqual(getBaseUrl(null), "");
  assert.strictEqual(getBaseUrl({ hostname: "localhost" }), "");
  assert.strictEqual(getBaseUrl({ hostname: "127.0.0.1" }), "");

  // Hosted cases
  assert.strictEqual(getBaseUrl({ hostname: "example.com", pathname: "/fund" }), "/fund");
  assert.strictEqual(getBaseUrl({ hostname: "example.com", pathname: "/fund/foo" }), "/fund");
  assert.strictEqual(getBaseUrl({ hostname: "example.com", pathname: "fund" }), "/fund");
  assert.strictEqual(getBaseUrl({ hostname: "example.com", pathname: "/other" }), "");
  assert.strictEqual(getBaseUrl({ hostname: "example.com", pathname: "" }), "");
});

test("getHoldingAssetClass logic", async () => {
  // Create mock environment
  global.window = { innerWidth: 1024 };
  global.document = { querySelector: () => null };

  const { getHoldingAssetClass } = await import("../js/config.js");

  // Invalid inputs
  assert.strictEqual(getHoldingAssetClass(null), "stock");
  assert.strictEqual(getHoldingAssetClass(123), "stock");
  assert.strictEqual(getHoldingAssetClass("   "), "stock");

  // Overrides
  assert.strictEqual(getHoldingAssetClass("VT"), "etf");
  assert.strictEqual(getHoldingAssetClass("vt"), "etf"); // Case insensitive
  assert.strictEqual(getHoldingAssetClass("QQQ"), "etf");

  // Likely fund tickers
  assert.strictEqual(getHoldingAssetClass("VTSAX"), "etf");

  // Stocks
  assert.strictEqual(getHoldingAssetClass("AAPL"), "stock");
  assert.strictEqual(getHoldingAssetClass("MSFT"), "stock");
});
