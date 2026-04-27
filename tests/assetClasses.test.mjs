import test from 'node:test';
import assert from 'node:assert';
import { isLikelyFundTicker } from '../js/config/assetClasses.js';

test('isLikelyFundTicker correctly identifies funds and ETFs', () => {
  // Invalid inputs
  assert.strictEqual(isLikelyFundTicker(null), false);
  assert.strictEqual(isLikelyFundTicker(undefined), false);
  assert.strictEqual(isLikelyFundTicker(123), false);
  assert.strictEqual(isLikelyFundTicker(''), false);
  assert.strictEqual(isLikelyFundTicker('   '), false);

  // Specific known funds
  assert.strictEqual(isLikelyFundTicker('VOO'), true);
  assert.strictEqual(isLikelyFundTicker('voo'), true); // Case insensitive
  assert.strictEqual(isLikelyFundTicker('  QQQ  '), true); // Trims whitespace
  assert.strictEqual(isLikelyFundTicker('VTSAX'), true); // Explicitly listed AND ends with X

  // General X-ending mutual funds (length > 4 and ends with X)
  assert.strictEqual(isLikelyFundTicker('SWPPX'), true); // Length 5, ends with X
  assert.strictEqual(isLikelyFundTicker('FBGRX'), true);

  // Negative cases
  assert.strictEqual(isLikelyFundTicker('AAPL'), false); // Normal stock
  assert.strictEqual(isLikelyFundTicker('MSFT'), false);
  assert.strictEqual(isLikelyFundTicker('TSLA'), false);

  // Edge cases
  assert.strictEqual(isLikelyFundTicker('X'), false); // Too short
  assert.strictEqual(isLikelyFundTicker('ABCX'), false); // Length exactly 4, ends with X
});
