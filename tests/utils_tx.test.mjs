import test from 'node:test';
import assert from 'node:assert';

test('utils/transactions basic utilities', async () => {
    // Before importing the module which relies on state and config,
    // we need to mock global dependencies used in config.js (e.g. window/document)
    global.window = { innerWidth: 1000 };
    global.document = {
        querySelector: () => null,
        getElementById: () => null
    };

    const { formatDate, escapeHtml, parseCSVLine, formatCurrencyCompact } = await import('../js/transactions/utils.js');

    assert.strictEqual(formatDate('2023-01-05T12:00:00Z'), '2023-01-05');

    assert.strictEqual(escapeHtml('<div class="test">&\'</div>'), '&lt;div class=&quot;test&quot;&gt;&amp;&#039;&lt;/div&gt;');
    assert.strictEqual(escapeHtml(123), 123);

    assert.deepStrictEqual(parseCSVLine('a,b,c'), ['a', 'b', 'c']);
    assert.deepStrictEqual(parseCSVLine('a,"b,c",d'), ['a', 'b,c', 'd']);
    assert.deepStrictEqual(parseCSVLine('a,"b""c",d'), ['a', 'b"c', 'd']);

    // coverage for formatCurrencyCompact missing lines
    // 267-268 (millions >= 10 but not 100 with non-CJK currencies)
    assert.strictEqual(formatCurrencyCompact(15_150_000, { currency: 'USD' }), '$15.2M');
    assert.strictEqual(formatCurrencyCompact(-15_150_000, { currency: 'USD' }), '-$15.2M');
    assert.strictEqual(formatCurrencyCompact(100_100_000, { currency: 'USD' }), '$100M');

    // 290-294 (thousands >= 10 and >= 100 with non-CJK currencies)
    assert.strictEqual(formatCurrencyCompact(150_000, { currency: 'USD' }), '$150k');
    assert.strictEqual(formatCurrencyCompact(15_150, { currency: 'USD' }), '$15.2k');
    assert.strictEqual(formatCurrencyCompact(1_500, { currency: 'USD' }), '$1.5k');

    // 304-305 (absolute >= 1, non-CJK, check for integer)
    assert.strictEqual(formatCurrencyCompact(15.001, { currency: 'USD' }), '$15');
});

test("formatCurrencyCompact handles non-CJK exact thousands and millions edge cases and tolerances", async () => {
    const { formatCurrencyCompact } = await import("../js/transactions/utils.js");

    // Testing millions branch limits
    assert.strictEqual(formatCurrencyCompact(15_000_000.08), "$15M"); // 15000000.08 / 1000000 = 15.00000008, diff to 15 is 0.00000008 < 0.1 so it returns 15M
    assert.strictEqual(formatCurrencyCompact(1_000_000.08), "$1M");
    assert.strictEqual(formatCurrencyCompact(15_120_000.08), "$15.1M"); // diff is 0.12 > 0.1, toFixed(1)
    assert.strictEqual(formatCurrencyCompact(15_000_000), "$15M");
    assert.strictEqual(formatCurrencyCompact(1_000_000), "$1M");

    // Testing thousands branch limits
    assert.strictEqual(formatCurrencyCompact(15_000.08), "$15k"); // 15000.08 / 1000 = 15.00008, diff to 15 is 0.00008 < 0.05 so it returns 15k
    assert.strictEqual(formatCurrencyCompact(1_000.08), "$1k");
    assert.strictEqual(formatCurrencyCompact(150_120.12), "$150k"); // >= 100, returns toFixed(0) => 150k
    assert.strictEqual(formatCurrencyCompact(15_120.12), "$15.1k"); // >= 10, diff > 0.05, returns toFixed(1) => 15.1k
    assert.strictEqual(formatCurrencyCompact(15_000), "$15k");
    assert.strictEqual(formatCurrencyCompact(1_000), "$1k");

    // Under thousands edge case
    assert.strictEqual(formatCurrencyCompact(1.08), "$1"); // Check for absolute < 1000 but not an integer and <0.1 tol
    assert.strictEqual(formatCurrencyCompact(1.5), "$2"); // Rounds below thousands
});

test("formatCurrencyCompact falls back to default zero for invalid or non-numeric values", async () => {
    // Arrange
    const { formatCurrencyCompact } = await import("../js/transactions/utils.js");
    const testCases = ["invalid", "not a number", NaN];

    // Act & Assert
    for (const testCase of testCases) {
        assert.strictEqual(formatCurrencyCompact(testCase, { currency: "USD" }), "$0");
    }
});

test("convertValueToCurrency returns unchanged original amount when target currency is USD or omitted", async () => {
    // Arrange
    const { convertValueToCurrency } = await import("../js/transactions/utils.js");
    const amount = 100;
    const date = "2023-01-01";

    // Act
    const resultMissingCurrency = convertValueToCurrency(amount, date, null);
    const resultUsd = convertValueToCurrency(amount, date, "USD");

    // Assert
    assert.strictEqual(resultMissingCurrency, amount);
    assert.strictEqual(resultUsd, amount);
});

test("convertBetweenCurrencies returns unchanged original amount for identical source and target currencies", async () => {
    // Arrange
    const { convertBetweenCurrencies } = await import("../js/transactions/utils.js");
    const amount = 100;

    // Act
    const resultUsdToUsd = convertBetweenCurrencies(amount, "USD", "2023-01-01", "USD");
    const resultEurToEur = convertBetweenCurrencies(amount, "EUR", "2023-01-01", "EUR");

    // Assert
    assert.strictEqual(resultUsdToUsd, amount);
    assert.strictEqual(resultEurToEur, amount);
});

test("formatCurrencyCompact handles CJK currency edge cases correctly", async () => {
    const originalDocument = global.document;
    const originalWindow = global.window;
    global.document = {
        querySelector: () => null,
        getElementById: () => null
    };
    global.window = { innerWidth: 1000 };

    const { formatCurrencyCompact } = await import("../js/transactions/utils.js");

    // Test CJK billion edge cases
    assert.strictEqual(formatCurrencyCompact(150_000_000_000, { currency: "JPY" }), "¥150B");
    assert.strictEqual(formatCurrencyCompact(15_150_000_000, { currency: "JPY" }), "¥15.2B");
    assert.strictEqual(formatCurrencyCompact(1_150_000_000, { currency: "JPY" }), "¥1.15B");

    // Test CJK million edge cases
    assert.strictEqual(formatCurrencyCompact(1_150_000, { currency: "JPY" }), "¥1.1M");
    assert.strictEqual(formatCurrencyCompact(1_000_000, { currency: "JPY" }), "¥1M");

    global.document = originalDocument;
    global.window = originalWindow;
});

test("formatCurrencyInlineValue falls back to selected currency when explicitly not provided", async () => {
    const originalDocument = global.document;
    const originalWindow = global.window;
    global.document = {
        querySelector: () => null,
        getElementById: () => null
    };
    global.window = { innerWidth: 1000 };

    const { formatCurrencyInlineValue } = await import("../js/transactions/utils.js");
    const { transactionState } = await import("../js/transactions/state.js");

    const originalSelected = transactionState.selectedCurrency;
    const originalSymbol = transactionState.currencySymbol;

    // Test transactionState selectedCurrency fallback
    transactionState.selectedCurrency = "GBP";
    transactionState.currencySymbol = "£";
    assert.strictEqual(formatCurrencyInlineValue(100), "£100");
    assert.strictEqual(formatCurrencyInlineValue(-100.5, { digits: 1 }), "-£100.5");

    // Reset state and test currencySymbol fallback
    transactionState.selectedCurrency = "XYZ";
    transactionState.currencySymbol = "€";
    assert.strictEqual(formatCurrencyInlineValue(100), "€100");

    // Test invalid arguments fallback (isFinite handling)
    assert.strictEqual(formatCurrencyInlineValue("invalid", { currency: "USD" }), "$0");
    assert.strictEqual(formatCurrencyInlineValue(NaN, { currency: "USD" }), "$0");

    transactionState.selectedCurrency = originalSelected;
    transactionState.currencySymbol = originalSymbol;
    global.document = originalDocument;
    global.window = originalWindow;
});

test("convertBetweenCurrencies uses closest historical FX rate when exact date is not available", async () => {
    const originalDocument = global.document;
    const originalWindow = global.window;
    global.document = {
        querySelector: () => null,
        getElementById: () => null
    };
    global.window = { innerWidth: 1000 };

    const { convertBetweenCurrencies } = await import("../js/transactions/utils.js");
    const { transactionState } = await import("../js/transactions/state.js");

    const originalRates = transactionState.fxRatesByCurrency;

    // Inject fake fx rates to hit the binary search code path
    transactionState.fxRatesByCurrency = {
        "EUR": {
            map: new Map([
                ["2023-01-01", 0.9],
                ["2023-01-03", 0.95],
                ["2023-01-05", 0.92]
            ]),
            sorted: [
                { date: "2023-01-01", ts: Date.parse("2023-01-01") },
                { date: "2023-01-03", ts: Date.parse("2023-01-03") },
                { date: "2023-01-05", ts: Date.parse("2023-01-05") }
            ]
        },
        "GBP": {
            map: new Map([
                ["2023-01-04", 0.8]
            ]),
            sorted: [
                { date: "2023-01-04", ts: Date.parse("2023-01-04") }
            ]
        }
    };

    // Exact match in map
    const amountMap = convertBetweenCurrencies(100, "USD", "2023-01-03", "EUR");
    assert.strictEqual(amountMap, 95);

    // Date between 01-03 and 01-05 (Not in Map, finds previous closest historical rate)
    const amountSearch = convertBetweenCurrencies(100, "USD", "2023-01-04", "EUR");
    assert.strictEqual(amountSearch, 95);

    // Convert source that is not USD
    const amountGbpToEur = convertBetweenCurrencies(100, "GBP", "2023-01-04", "EUR");
    // 100 GBP / 0.8 GBP/USD = 125 USD. 125 USD * 0.95 EUR/USD = 118.75 EUR
    assert.strictEqual(amountGbpToEur, 118.75);

    // Coverage for default handling in convertBetweenCurrencies
    const fallbackToUsdFrom = convertBetweenCurrencies(100, "   ", "2023-01-04", "EUR");
    assert.strictEqual(fallbackToUsdFrom, 95);

    const fallbackToUsdTo = convertBetweenCurrencies(100, "EUR", "2023-01-04", "   ");
    // 100 EUR / 0.95 EUR/USD = 105.26315789473685 USD
    assert.ok(Math.abs(fallbackToUsdTo - 105.263) < 0.01);

    transactionState.fxRatesByCurrency = originalRates;
    global.document = originalDocument;
    global.window = originalWindow;
});
