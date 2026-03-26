import assert from "assert";

// Mock document globally
global.window = {
  location: { hostname: "example.com", pathname: "/fund" },
  innerWidth: 1000,
};

global.document = {
  querySelector: (selector) => null,
};

// Use dynamic import so that document is already defined
async function runTests() {
  const {
    getBaseUrl,
    getHoldingAssetClass,
    CALENDAR_CONFIG,
    TICKER_TO_LOGO_MAP,
    UI_BREAKPOINTS,
    BASE_URL,
  } = await import("../js/config.js");

  console.log("🧪 Config Utils Tests\n");

  let passed = 0;
  let failed = 0;

  try {
    assert.strictEqual(getBaseUrl(null), "");
    assert.strictEqual(getBaseUrl(undefined), "");
    assert.strictEqual(getBaseUrl({}), "");

    assert.strictEqual(getBaseUrl({ hostname: "localhost" }), "");
    assert.strictEqual(getBaseUrl({ hostname: "127.0.0.1" }), "");

    assert.strictEqual(
      getBaseUrl({ hostname: "example.com", pathname: null }),
      "",
    );
    assert.strictEqual(
      getBaseUrl({ hostname: "example.com", pathname: "" }),
      "",
    );
    assert.strictEqual(
      getBaseUrl({ hostname: "example.com", pathname: "/other" }),
      "",
    );
    assert.strictEqual(
      getBaseUrl({ hostname: "example.com", pathname: "/fund" }),
      "/fund",
    );
    assert.strictEqual(
      getBaseUrl({ hostname: "example.com", pathname: "/fund/" }),
      "/fund",
    );
    assert.strictEqual(
      getBaseUrl({ hostname: "example.com", pathname: "fund" }),
      "/fund",
    );

    // Check BASE_URL initialization behavior
    assert.strictEqual(BASE_URL, "/fund");

    passed++;
  } catch (e) {
    console.error("getBaseUrl tests failed:", e);
    failed++;
  }

  try {
    assert.strictEqual(getHoldingAssetClass(null), "stock");
    assert.strictEqual(getHoldingAssetClass("   "), "stock");
    assert.strictEqual(getHoldingAssetClass("AAPL"), "stock");

    // Override cases - ASSET_CLASS_OVERRIDES
    assert.strictEqual(getHoldingAssetClass("VT"), "etf");

    // isLikelyFundTicker cases
    assert.strictEqual(getHoldingAssetClass("VTSAX"), "etf");
    passed++;
  } catch (e) {
    console.error("getHoldingAssetClass tests failed:", e);
    failed++;
  }

  try {
    assert.ok(typeof CALENDAR_CONFIG.subDomain.label() === "string");
    assert.ok(typeof CALENDAR_CONFIG.subDomain.color() === "string");
    passed++;
  } catch (e) {
    console.error("CALENDAR_CONFIG functions tests failed:", e);
    failed++;
  }

  if (failed > 0) {
    process.exitCode = 1;
  }
}

runTests().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
