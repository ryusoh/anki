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

test('isLikelyFundTicker boundary and type checks', () => {
  // Complex types
  assert.strictEqual(isLikelyFundTicker([]), false);
  assert.strictEqual(isLikelyFundTicker({}), false);
  assert.strictEqual(isLikelyFundTicker(true), false);
  assert.strictEqual(isLikelyFundTicker(false), false);

  // Floating point / number-like strings
  assert.strictEqual(isLikelyFundTicker(12.34), false);
  assert.strictEqual(isLikelyFundTicker('12.34'), false);

  // Very long invalid string
  const longStr = 'A'.repeat(100);
  assert.strictEqual(isLikelyFundTicker(longStr), false);

  // Very long valid string matching X condition
  const longFundStr = 'A'.repeat(100) + 'X';
  assert.strictEqual(isLikelyFundTicker(longFundStr), true);
});
