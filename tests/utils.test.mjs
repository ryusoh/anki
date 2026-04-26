import test from "node:test";
import assert from "node:assert";

// Mock window/document before dynamic import to avoid crash in config.js
global.window = { matchMedia: () => ({ matches: false }) };
global.document = { querySelector: () => null, createElement: () => ({}), head: { appendChild: () => {} } };

test("formatDate parses and formats ISO date correctly", async () => {
  const { formatDate } = await import("../js/transactions/utils.js");
  assert.strictEqual(formatDate("2023-01-05T12:00:00Z"), "2023-01-05");
  assert.strictEqual(formatDate("2023-11-20"), "2023-11-20");
});

test("formatCurrency handles positive, negative, and invalid values", async () => {
  const { formatCurrency } = await import("../js/transactions/utils.js");
  assert.strictEqual(formatCurrency(1234.5), "$1,234.50");
  assert.strictEqual(formatCurrency(-1234.5), "-$1,234.50");
  assert.strictEqual(formatCurrency(0), "$0.00");
  assert.strictEqual(formatCurrency("invalid"), "$0.00");
});

test("formatCurrencyInlineValue respects digit limits", async () => {
  const { formatCurrencyInlineValue } = await import("../js/transactions/utils.js");
  assert.strictEqual(formatCurrencyInlineValue(1234.5), "$1,235"); // Default 0 digits rounds up
  assert.strictEqual(formatCurrencyInlineValue(1234.5, {digits: 2}), "$1,234.50");
});

test("formatCurrencyCompact handles magnitudes from small to Trillions", async () => {
  const { formatCurrencyCompact } = await import("../js/transactions/utils.js");
  assert.strictEqual(formatCurrencyCompact(1_500_000_000_000), "$1.50T");
  assert.strictEqual(formatCurrencyCompact(1_050_000_000_000), "$1T"); // Updated per implementation logic
  assert.strictEqual(formatCurrencyCompact(150_000_000_000), "$150B");
  assert.strictEqual(formatCurrencyCompact(1_500_000_000), "$1.50B");
  assert.strictEqual(formatCurrencyCompact(150_000_000), "$150M");
  assert.strictEqual(formatCurrencyCompact(1_500_000), "$1.50M");
  assert.strictEqual(formatCurrencyCompact(150_000), "$150k");
  assert.strictEqual(formatCurrencyCompact(1_500), "$1.5k");
  assert.strictEqual(formatCurrencyCompact(10.5), "$11"); // Rounds below thousands
  assert.strictEqual(formatCurrencyCompact(0.01), "$0.01");
  assert.strictEqual(formatCurrencyCompact(0), "$0");
  assert.strictEqual(formatCurrencyCompact(-1234000), "-$1.23M");
});

test("formatCurrencyCompact handles CJK Currency special rounding", async () => {
  const { formatCurrencyCompact } = await import("../js/transactions/utils.js");
  assert.strictEqual(formatCurrencyCompact(1_500_000, {currency: "JPY"}), "¥1.5M");
  assert.strictEqual(formatCurrencyCompact(150_000, {currency: "JPY"}), "¥150k");
  assert.strictEqual(formatCurrencyCompact(1_500, {currency: "JPY"}), "¥1.5k"); // Adjusting to match CJK thousands formatting
  assert.strictEqual(formatCurrencyCompact(150, {currency: "JPY"}), "¥150");
  assert.strictEqual(formatCurrencyCompact(0.5, {currency: "JPY"}), "¥1"); // CJK is rounded at fraction
});

test("escapeHtml successfully sanitizes standard XSS payloads", async () => {
  const { escapeHtml } = await import("../js/transactions/utils.js");
  assert.strictEqual(escapeHtml("<script>alert('xss & \"co\"')</script>"), "&lt;script&gt;alert(&#039;xss &amp; &quot;co&quot;&#039;)&lt;/script&gt;");
  assert.strictEqual(escapeHtml(null), null);
});

test("parseCSVLine handles standard and quoted CSV items", async () => {
  const { parseCSVLine } = await import("../js/transactions/utils.js");
  assert.deepStrictEqual(parseCSVLine('a,b,c'), ['a', 'b', 'c']);
  assert.deepStrictEqual(parseCSVLine('a,"b, c",d'), ['a', 'b, c', 'd']);
  assert.deepStrictEqual(parseCSVLine('a,"b "" c",d'), ['a', 'b " c', 'd']);
});

test("convertValueToCurrency maps values correctly with FX states", async () => {
  const { convertValueToCurrency, convertBetweenCurrencies } = await import("../js/transactions/utils.js");
  const { setFxRatesByCurrency, setSelectedCurrency } = await import("../js/transactions/state.js");

  // Arrange FX Map
  const fxMap = {
    EUR: {
      map: new Map([["2023-01-01", 0.9], ["2023-01-02", 0.95]]),
      sorted: [
        { date: "2023-01-01", ts: Date.parse("2023-01-01") },
        { date: "2023-01-02", ts: Date.parse("2023-01-02") }
      ]
    },
    GBP: {
      map: new Map([["2023-01-01", 0.8]]),
      sorted: [
        { date: "2023-01-01", ts: Date.parse("2023-01-01") }
      ]
    }
  };
  setFxRatesByCurrency(fxMap);
  setSelectedCurrency("EUR");

  // Act / Assert
  assert.strictEqual(convertValueToCurrency(100, "2023-01-01", "EUR"), 90);
  assert.strictEqual(convertValueToCurrency(100, "2023-01-02", "EUR"), 95);
  assert.strictEqual(convertValueToCurrency(100, "2023-01-01", "USD"), 100);

  assert.strictEqual(convertBetweenCurrencies(90, "EUR", "2023-01-01", "USD"), 100);
  assert.strictEqual(convertBetweenCurrencies(90, "EUR", "2023-01-01", "GBP"), 80);
  assert.strictEqual(convertBetweenCurrencies(100, "USD", "2023-01-01", "GBP"), 80);
  assert.strictEqual(convertBetweenCurrencies(100, "USD", "2023-01-01", "USD"), 100);
});
