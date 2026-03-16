import assert from 'assert';

// Minimal mock for browser environment
const windowMock = {
  Chart: class {},
  customStatsData: {
    futureDue: [],
    futureDueByDeck: {},
    reviewStats: []
  },
  innerWidth: 1024
};
global.window = windowMock;
global.self = windowMock;
global.document = {
  getElementById: () => ({
    classList: { add: () => {}, remove: () => {} },
    innerHTML: '',
    style: {}
  }),
  querySelector: () => null
};

async function run() {
    // Import the function to test AFTER setting globals
    const { validateCommand } = await import('../js/commands/handler.js');

    function runTests() {
      console.log('🧪 Testing validateCommand from handler.js\n');

      // Test Case 1: Exact matches
      console.log('📋 Test Case 1: Exact matches');
      const validCommands = ['help', 'plot due', 'reviews', '1m', 'all', 'r'];
      validCommands.forEach(cmd => {
        const result = validateCommand(cmd);
        assert.strictEqual(result.valid, true, `"${cmd}" should be valid`);
        console.log(`   ✓ "${cmd}" is valid`);
      });

      // Test Case 2: Case-insensitive matches
      console.log('\n📋 Test Case 2: Case-insensitive matches');
      const caseTests = ['HELP', 'Plot Due', 'REVIEWS', '1M'];
      caseTests.forEach(cmd => {
        const result = validateCommand(cmd);
        assert.strictEqual(result.valid, true, `"${cmd}" (case-insensitive) should be valid`);
        console.log(`   ✓ "${cmd}" is valid`);
      });

      // Test Case 3: Partial matches with suggestions
      console.log('\n📋 Test Case 3: Partial matches and suggestions');
      const partialTests = [
        { prefix: 'pl', expected: 'plot' },
        { prefix: 'plot d', expected: 'plot due' },
        { prefix: 'rev', expected: 'reviews' }
      ];
      partialTests.forEach(({ prefix, expected }) => {
        const result = validateCommand(prefix);
        assert.strictEqual(result.valid, false, `"${prefix}" should not be an exact match`);
        assert.strictEqual(result.isPartial, true, `"${prefix}" should be a partial match`);
        assert.ok(result.suggestions.length > 0, `"${prefix}" should have suggestions`);
        assert.ok(result.suggestions.includes(expected), `Suggestions for "${prefix}" should include "${expected}"`);
        console.log(`   ✓ "${prefix}" returns suggestions including "${expected}"`);
      });

      // Test Case 4: Invalid commands
      console.log('\n📋 Test Case 4: Invalid commands');
      const invalidCommands = ['not_a_command', 'plot_everything', '!!!!'];
      invalidCommands.forEach(cmd => {
        const result = validateCommand(cmd);
        assert.strictEqual(result.valid, false, `"${cmd}" should be invalid`);
        assert.strictEqual(result.isPartial, false, `"${cmd}" should not be a partial match`);
        console.log(`   ✓ "${cmd}" is correctly rejected`);
      });

      // Test Case 5: Empty and whitespace
      console.log('\n📋 Test Case 5: Empty and whitespace');
      const emptyResult = validateCommand('');
      assert.strictEqual(emptyResult.valid, false);
      assert.ok(emptyResult.suggestions.length > 0);
      console.log('   ✓ Empty string handled');

      const spaceResult = validateCommand('   ');
      assert.strictEqual(spaceResult.valid, false);
      console.log('   ✓ Whitespace handled');

      console.log('\n✅ All validateCommand tests passed!');
    }

    try {
      runTests();
    } catch (error) {
      console.error('\n❌ Test failed:');
      console.error(error);
      process.exit(1);
    }
}

run();
