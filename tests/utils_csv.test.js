import assert from 'assert';

global.document = {
  querySelector: () => null
};
global.window = {
  innerWidth: 1024,
  location: { search: '' },
  localStorage: { getItem: () => null, setItem: () => {} }
};

async function runTests() {
  const { parseCSVLine } = await import('../js/transactions/utils.js');

  console.log('--- utils_csv.test.js ---');

  // Basic comma separation
  assert.deepStrictEqual(parseCSVLine('a,b,c'), ['a', 'b', 'c']);

  // Trimming spaces around unquoted values
  assert.deepStrictEqual(parseCSVLine('  a  , b ,c '), ['a', 'b', 'c']);

  // Quotes handling
  assert.deepStrictEqual(parseCSVLine('"a,b",c'), ['a,b', 'c']);

  // Empty values
  assert.deepStrictEqual(parseCSVLine('a,,c'), ['a', '', 'c']);
  assert.deepStrictEqual(parseCSVLine(',b,c'), ['', 'b', 'c']);
  assert.deepStrictEqual(parseCSVLine('a,b,'), ['a', 'b', '']);
  assert.deepStrictEqual(parseCSVLine(','), ['', '']);

  // Escaped quotes inside quotes
  assert.deepStrictEqual(parseCSVLine('"a""b",c'), ['a"b', 'c']);

  // Quotes with spaces inside (spaces inside quotes are preserved, outside trimmed)
  assert.deepStrictEqual(parseCSVLine('  " a "  , b '), ['a', 'b']);

  delete global.document;
  delete global.window;
  console.log('All tests passed.');
}

runTests().catch(e => {
  console.error(e);
  process.exitCode = 1;
});
