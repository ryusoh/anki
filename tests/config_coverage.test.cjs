const test = require("node:test");
const assert = require("node:assert");

// Mock global window and document
global.window = {
  innerWidth: 1024
};
global.document = {
  querySelector: () => null
};

test("js/config.js coverage additions", async (t) => {
  const config = await import("../js/config.js");

  // Tests for getBaseUrl and implicitly isServedFromFundDirectory
  await t.test("getBaseUrl correctly identifies fund paths", () => {
    // 1. null/undefined location
    assert.strictEqual(config.getBaseUrl(null), "");

    // 2. Localhost
    assert.strictEqual(
      config.getBaseUrl({ hostname: "localhost", pathname: "/fund/index.html" }),
      ""
    );

    // 3. Not localhost, empty pathname
    assert.strictEqual(
      config.getBaseUrl({ hostname: "example.com", pathname: "" }),
      ""
    );

    // 4. Not localhost, invalid pathname
    assert.strictEqual(
      config.getBaseUrl({ hostname: "example.com", pathname: null }),
      ""
    );

    // 5. Not localhost, starts with /fund
    assert.strictEqual(
      config.getBaseUrl({ hostname: "example.com", pathname: "/fund/index.html" }),
      "/fund"
    );

    // 6. Not localhost, starts with fund (no slash)
    assert.strictEqual(
      config.getBaseUrl({ hostname: "example.com", pathname: "fund/index.html" }),
      "/fund"
    );

    // 7. Not localhost, starts with something else
    assert.strictEqual(
      config.getBaseUrl({ hostname: "example.com", pathname: "/other/index.html" }),
      ""
    );
  });
});

test("js/config/assetClasses.js coverage additions", async (t) => {
  const { isLikelyFundTicker } = await import("../js/config/assetClasses.js");

  await t.test("isLikelyFundTicker correctly identifies funds", () => {
    // 1. Not a string
    assert.strictEqual(isLikelyFundTicker(123), false);
    assert.strictEqual(isLikelyFundTicker(null), false);

    // 2. Empty or whitespace
    assert.strictEqual(isLikelyFundTicker(""), false);
    assert.strictEqual(isLikelyFundTicker("   "), false);

    // 3. Known overrides
    assert.strictEqual(isLikelyFundTicker("VTI"), true);
    assert.strictEqual(isLikelyFundTicker("vti"), true);

    // 4. Ends with X and length > 4
    assert.strictEqual(isLikelyFundTicker("VTSAX"), true);
    assert.strictEqual(isLikelyFundTicker("vtsax"), true);

    // 5. Ends with X but length <= 4
    assert.strictEqual(isLikelyFundTicker("ARXX"), false);

    // 6. Normal stock
    assert.strictEqual(isLikelyFundTicker("AAPL"), false);
  });
});

test("js/config.js getHoldingAssetClass coverage additions", async (t) => {
  const config = await import("../js/config.js");

  await t.test("getHoldingAssetClass correctly identifies asset classes", () => {
    // 1. Not a string
    assert.strictEqual(config.getHoldingAssetClass(123), "stock");
    assert.strictEqual(config.getHoldingAssetClass(null), "stock");

    // 2. Empty or whitespace
    assert.strictEqual(config.getHoldingAssetClass(""), "stock");
    assert.strictEqual(config.getHoldingAssetClass("   "), "stock");
  });
});

test("js/utils/host.js coverage additions", async (t) => {
  const { isLocalhost } = await import("../js/utils/host.js");

  await t.test("isLocalhost correctly identifies local domains", () => {
    // 1. null/empty
    assert.strictEqual(isLocalhost(null), false);
    assert.strictEqual(isLocalhost(""), false);

    // 2. Exact match localhost domains
    assert.strictEqual(isLocalhost("localhost"), true);
    assert.strictEqual(isLocalhost("127.0.0.1"), true);
    assert.strictEqual(isLocalhost("::1"), true);
    assert.strictEqual(isLocalhost("0.0.0.0"), true);

    // 3. .local
    assert.strictEqual(isLocalhost("my-macbook.local"), true);

    // 4. Private IPv4
    assert.strictEqual(isLocalhost("10.0.0.1"), true); // 10.x.x.x
    assert.strictEqual(isLocalhost("192.168.1.100"), true); // 192.168.x.x
    assert.strictEqual(isLocalhost("172.16.0.1"), true); // 172.16.x.x
    assert.strictEqual(isLocalhost("172.31.255.255"), true); // 172.31.x.x
    assert.strictEqual(isLocalhost("172.15.0.1"), false); // out of range 172.16-31
    assert.strictEqual(isLocalhost("172.32.0.1"), false); // out of range 172.16-31
    assert.strictEqual(isLocalhost("192.169.1.1"), false); // out of range 192.168

    // 5. External IPs / Domains
    assert.strictEqual(isLocalhost("8.8.8.8"), false);
    assert.strictEqual(isLocalhost("example.com"), false);

    // 6. Invalid formats
    assert.strictEqual(isLocalhost("192.168.1"), false); // not 4 octets
  });
});

test("js/config.js getHoldingAssetClass override coverage additions", async (t) => {
  const config = await import("../js/config.js");

  await t.test("getHoldingAssetClass override hit", () => {
    // 3. Override hit
    assert.strictEqual(config.getHoldingAssetClass("VTI"), "etf");

    // 4. isLikelyFundTicker hit
    assert.strictEqual(config.getHoldingAssetClass("VTSAX"), "etf");

    // 5. stock hit
    assert.strictEqual(config.getHoldingAssetClass("AAPL"), "stock");
  });
});

test("js/config/assetClasses.js extra coverage additions", async (t) => {
  const { isLikelyFundTicker } = await import("../js/config/assetClasses.js");

  await t.test("isLikelyFundTicker edge cases", () => {
    // Ends with X but not an override and length > 4 (already tested VTSAX)
    // Add explicitly an invalid test case
    assert.strictEqual(isLikelyFundTicker("12345X"), true);
  });
});
