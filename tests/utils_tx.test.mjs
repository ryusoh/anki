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
