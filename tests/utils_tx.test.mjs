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

    const { formatDate, escapeHtml, parseCSVLine } = await import('../js/transactions/utils.js');

    assert.strictEqual(formatDate('2023-01-05T12:00:00Z'), '2023-01-05');

    assert.strictEqual(escapeHtml('<div class="test">&\'</div>'), '&lt;div class=&quot;test&quot;&gt;&amp;&#039;&lt;/div&gt;');
    assert.strictEqual(escapeHtml(123), 123);

    assert.deepStrictEqual(parseCSVLine('a,b,c'), ['a', 'b', 'c']);
    assert.deepStrictEqual(parseCSVLine('a,"b,c",d'), ['a', 'b,c', 'd']);
    assert.deepStrictEqual(parseCSVLine('a,"b""c",d'), ['a', 'b"c', 'd']);
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
