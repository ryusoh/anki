import assert from 'assert';

/**
 * Regression test for Command Handler Regex Bug
 * 
 * This test specifically targets the issue where 's+' was used instead of '\s+' 
 * in handler.js regexes, causing commands with spaces to fail.
 */

// Minimal mock for browser environment needed by handler.js
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
  getElementById: (id) => ({
    id,
    classList: { add: () => {}, remove: () => {}, contains: () => false },
    innerHTML: '',
    style: {},
    appendChild: () => {},
    scrollTop: 0,
    scrollHeight: 0
  }),
  querySelector: () => null,
  querySelectorAll: () => []
};

async function runRegressionTests() {
    console.log('🧪 Running Command Handler Regression Tests (Real Implementation)\n');
    
    // Import the real handleCommand
    const { handleCommand } = await import('../js/commands/handler.js');

    const appendLine = (text, variant) => {
        // Mock terminal output
    };

    const testCases = [
        { input: 'plot due', expectedCmd: 'plot-due' },
        { input: 'plot reviews', expectedCmd: 'plot-reviews' },
        { input: 'due deck', expectedCmd: 'due-deck' },
        { input: 'plot retention', expectedCmd: 'plot-retention' },
        { input: 'show due', expectedCmd: 'due' },
        { input: 'plot reviews time', expectedCmd: 'plot-reviews-time' },
        { input: 'plot reviews cumulative', expectedCmd: 'plot-reviews-cumulative' }
    ];

    let passed = 0;
    let failed = 0;

    testCases.forEach(({ input, expectedCmd }) => {
        try {
            const result = handleCommand(input, appendLine);
            assert.strictEqual(result.handled, true, `"${input}" should be handled`);
            if (expectedCmd) {
                assert.strictEqual(result.command, expectedCmd, `"${input}" should map to command: ${expectedCmd}`);
            }
            console.log(`   ✓ "${input}" correctly handled`);
            passed++;
        } catch (e) {
            console.log(`   ✗ "${input}" FAILED: ${e.message}`);
            failed++;
        }
    });

    console.log('\n📋 Testing spacing variations');
    const spacingTests = [
        { input: 'plot   due', expectedCmd: 'plot-due' },
        { input: 'reviews    time', expectedCmd: 'reviews-time' }
    ];

    spacingTests.forEach(({ input, expectedCmd }) => {
        try {
            const result = handleCommand(input, appendLine);
            assert.strictEqual(result.handled, true, `"${input}" (extra spaces) should be handled`);
            console.log(`   ✓ "${input}" (extra spaces) correctly handled`);
            passed++;
        } catch (e) {
            console.log(`   ✗ "${input}" (extra spaces) FAILED: ${e.message}`);
            failed++;
        }
    });

    console.log(`\n📊 Results: ${passed} passed, ${failed} failed`);
    
    if (failed > 0) {
        process.exit(1);
    }
}

runRegressionTests().catch(err => {
    console.error(err);
    process.exit(1);
});
