import test from 'node:test';
import assert from 'node:assert';

test('config coverage getBaseUrl', async () => {
    // Mock document and window BEFORE importing config.js
    global.window = {
        innerWidth: 1024,
        location: {
            hostname: 'example.com',
            pathname: '/fund/data'
        }
    };
    global.document = {
        querySelector: () => null,
    };

    const { getBaseUrl } = await import('../js/config.js');

    assert.strictEqual(getBaseUrl(null), '');
    assert.strictEqual(getBaseUrl({ hostname: 'localhost', pathname: '/fund/data' }), '');
    assert.strictEqual(getBaseUrl({ hostname: 'example.com', pathname: '/other/data' }), '');
    assert.strictEqual(getBaseUrl({ hostname: 'example.com', pathname: '/fund/data' }), '/fund');
    assert.strictEqual(getBaseUrl({}), '');
});
