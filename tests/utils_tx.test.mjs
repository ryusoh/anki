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
