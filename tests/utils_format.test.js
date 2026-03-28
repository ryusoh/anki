import assert from "assert";

// Mock global objects
global.document = {
  querySelector: () => null,
};
global.window = {
  innerWidth: 1024,
  location: { search: "" },
  localStorage: { getItem: () => null, setItem: () => {} },
};

// Now we can import dynamically
async function runTests() {
  const {
    formatDate,
    escapeHtml,
    parseCSVLine,
    formatCurrencyCompact,
    formatCurrency,
    formatCurrencyInlineValue,
    convertValueToCurrency,
    convertBetweenCurrencies,
  } = await import("../js/transactions/utils.js");
  const { setSelectedCurrency, setFxRatesByCurrency, transactionState } =
    await import("../js/transactions/state.js");

  console.log("--- utils_format.test.js ---");

  // Test: formatDate
  assert.strictEqual(
    formatDate("2023-01-05T12:00:00Z"),
    "2023-01-05",
    "formatDate should format ISO string correctly",
  );
  assert.strictEqual(
    formatDate(new Date("2023-01-05T12:00:00Z")),
    "2023-01-05",
    "formatDate should format Date correctly",
  );

  // Test: escapeHtml
  assert.strictEqual(
    escapeHtml('<script>alert("1")</script>&\''),
    "&lt;script&gt;alert(&quot;1&quot;)&lt;/script&gt;&amp;&#039;",
    "escapeHtml should escape all special characters",
  );
  assert.strictEqual(
    escapeHtml(123),
    123,
    "escapeHtml should return non-strings unchanged",
  );

  // Test: parseCSVLine
  assert.deepStrictEqual(
    parseCSVLine("1,2,3"),
    ["1", "2", "3"],
    "parseCSVLine should split by comma",
  );
  assert.deepStrictEqual(
    parseCSVLine('1,"2,3",4'),
    ["1", "2,3", "4"],
    "parseCSVLine should handle quotes",
  );
  assert.deepStrictEqual(
    parseCSVLine('1,"2,""3""",4'),
    ["1", '2,"3"', "4"],
    "parseCSVLine should handle escaped quotes",
  );

  // Test: formatCurrencyCompact
  setSelectedCurrency("USD");
  assert.strictEqual(formatCurrencyCompact(1500), "$1.5k");
  assert.strictEqual(formatCurrencyCompact(1500000), "$1.50M");
  assert.strictEqual(formatCurrencyCompact(1000000), "$1M");
  assert.strictEqual(formatCurrencyCompact(1000000000), "$1B");
  assert.strictEqual(formatCurrencyCompact(1500000000), "$1.50B");
  assert.strictEqual(formatCurrencyCompact(1000000000000), "$1T");
  assert.strictEqual(formatCurrencyCompact(1500000000000), "$1.50T");
  assert.strictEqual(formatCurrencyCompact(0.001), "$0");
  assert.strictEqual(formatCurrencyCompact(0.004), "$0"); // less than 0.005 edge case
  assert.strictEqual(formatCurrencyCompact(0.006), "$0.01"); // above 0.005 edge case
  assert.strictEqual(formatCurrencyCompact(-1500), "-$1.5k");
  assert.strictEqual(formatCurrencyCompact("abc"), "$0");

  assert.strictEqual(formatCurrencyCompact(10000000000000), "$10T");
  assert.strictEqual(formatCurrencyCompact(100000000000000), "$100T");
  assert.strictEqual(formatCurrencyCompact(10000000000), "$10B");
  assert.strictEqual(formatCurrencyCompact(100000000000), "$100B");
  assert.strictEqual(formatCurrencyCompact(10000000), "$10M");
  assert.strictEqual(formatCurrencyCompact(100000000), "$100M");
  assert.strictEqual(formatCurrencyCompact(10000), "$10k");
  assert.strictEqual(formatCurrencyCompact(100000), "$100k");

  // Custom non-integer edge cases for non-CJK
  assert.strictEqual(formatCurrencyCompact(10), "$10");
  assert.strictEqual(formatCurrencyCompact(10.5), "$11"); // Number rounding for non-CJK < 1000 check

  // formatCurrencyCompact with CJK Currency
  assert.strictEqual(
    formatCurrencyCompact(1500000000000, { currency: "CNY" }),
    "¥1.50T",
  );
  assert.strictEqual(
    formatCurrencyCompact(1000000000000, { currency: "JPY" }),
    "¥1.00T",
  );
  assert.strictEqual(
    formatCurrencyCompact(10000000000000, { currency: "KRW" }),
    "₩10.0T",
  );
  assert.strictEqual(
    formatCurrencyCompact(100000000000000, { currency: "CNY" }),
    "¥100T",
  );

  assert.strictEqual(
    formatCurrencyCompact(1500000000, { currency: "CNY" }),
    "¥1.50B",
  );
  assert.strictEqual(
    formatCurrencyCompact(1000000000, { currency: "JPY" }),
    "¥1.00B",
  );
  assert.strictEqual(
    formatCurrencyCompact(10000000000, { currency: "KRW" }),
    "₩10.0B",
  );
  assert.strictEqual(
    formatCurrencyCompact(100000000000, { currency: "CNY" }),
    "¥100B",
  );

  assert.strictEqual(
    formatCurrencyCompact(1500000, { currency: "CNY" }),
    "¥1.5M",
  );
  assert.strictEqual(
    formatCurrencyCompact(1000000, { currency: "JPY" }),
    "¥1M",
  );
  assert.strictEqual(
    formatCurrencyCompact(10000000, { currency: "KRW" }),
    "₩10M",
  ); // million checks >= 10 logic
  assert.strictEqual(
    formatCurrencyCompact(100000000, { currency: "CNY" }),
    "¥100M",
  );

  assert.strictEqual(formatCurrencyCompact(1500, { currency: "CNY" }), "¥1.5k");
  assert.strictEqual(formatCurrencyCompact(1000, { currency: "JPY" }), "¥1k");
  assert.strictEqual(formatCurrencyCompact(10000, { currency: "KRW" }), "₩10k"); // thousand checks >= 10 logic
  assert.strictEqual(
    formatCurrencyCompact(100000, { currency: "CNY" }),
    "¥100k",
  );

  assert.strictEqual(formatCurrencyCompact(10, { currency: "CNY" }), "¥10");
  assert.strictEqual(formatCurrencyCompact(10.5, { currency: "JPY" }), "¥11");
  assert.strictEqual(formatCurrencyCompact(0.5, { currency: "KRW" }), "₩1");

  // Edge cases for non-CJK exact rounding inside the k logic
  assert.strictEqual(formatCurrencyCompact(1050), "$1.1k");
  assert.strictEqual(formatCurrencyCompact(1001), "$1k"); // rounds to 1k based on absolute - Math.round(thousands) < 0.05
  assert.strictEqual(formatCurrencyCompact(1000001), "$1M");
  assert.strictEqual(formatCurrencyCompact(1000000001), "$1B");

  // Non-CJK fallback formatting paths for >= 100, >= 10, etc when not effectively an integer
  assert.strictEqual(formatCurrencyCompact(150000000000), "$150B");
  assert.strictEqual(formatCurrencyCompact(15000000000), "$15B");
  assert.strictEqual(formatCurrencyCompact(150000000), "$150M");
  assert.strictEqual(formatCurrencyCompact(15000000), "$15M");
  assert.strictEqual(formatCurrencyCompact(150000), "$150k");
  assert.strictEqual(formatCurrencyCompact(15000), "$15k"); // Non-CJK thousands >= 10 fallback
  assert.strictEqual(formatCurrencyCompact(15500), "$15.5k");
  assert.strictEqual(formatCurrencyCompact(155500), "$156k"); // Non-CJK thousands >= 100 fallback
  assert.strictEqual(formatCurrencyCompact(15500000), "$15.5M"); // Non-CJK millions >= 10 fallback
  assert.strictEqual(formatCurrencyCompact(155500000), "$156M"); // Non-CJK millions >= 100 fallback
  assert.strictEqual(formatCurrencyCompact(15500000000), "$15.5B"); // Non-CJK billions >= 10 fallback
  assert.strictEqual(formatCurrencyCompact(155500000000), "$156B"); // Non-CJK billions >= 100 fallback

  // formatCurrency / formatCurrencyInlineValue
  setSelectedCurrency("USD");
  assert.strictEqual(formatCurrency(1500), "$1,500.00");
  assert.strictEqual(formatCurrency(-1500), "-$1,500.00");
  assert.strictEqual(formatCurrency("abc"), "$0.00");
  assert.strictEqual(formatCurrencyInlineValue(1500.5), "$1,501");
  assert.strictEqual(
    formatCurrencyInlineValue(1500.5, { digits: 2 }),
    "$1,500.50",
  );
  assert.strictEqual(formatCurrencyInlineValue("abc", { digits: 2 }), "$0.00");

  // test convertValueToCurrency
  assert.strictEqual(convertValueToCurrency("abc", "2023-01-01", "USD"), 0);
  assert.strictEqual(convertValueToCurrency(100, "2023-01-01", "USD"), 100);

  // mock fxRates
  setFxRatesByCurrency({
    EUR: {
      map: new Map([
        ["2023-01-01", 0.9],
        ["2023-01-05", 0.85],
      ]),
      sorted: [
        { date: "2023-01-01", ts: Date.parse("2023-01-01") },
        { date: "2023-01-05", ts: Date.parse("2023-01-05") },
      ],
    },
  });

  assert.strictEqual(convertValueToCurrency(100, "2023-01-01", "EUR"), 90);
  assert.strictEqual(convertValueToCurrency(100, "2023-01-05", "EUR"), 85);
  // binary search in findFxRate returns nearest index. '2023-01-03' is larger than '2023-01-01'
  assert.strictEqual(convertValueToCurrency(100, "2023-01-03", "EUR"), 90); // Should pick the closest before or after logic. Let's trace findFxRate

  assert.strictEqual(
    convertBetweenCurrencies(100, "EUR", "2023-01-01", "USD"),
    100 / 0.9,
  );
  assert.strictEqual(
    convertBetweenCurrencies(100, "USD", "2023-01-01", "EUR"),
    100 * 0.9,
  );
  assert.strictEqual(
    convertBetweenCurrencies(100, "EUR", "2023-01-01", "EUR"),
    100,
  );

  // Some invalid rates checks
  assert.strictEqual(
    convertBetweenCurrencies(100, "EUR", "1999-01-01", "USD"),
    100 / 0.9,
  );

  // Teardown globals
  delete global.document;
  delete global.window;

  console.log("All tests passed.");
}

runTests().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
