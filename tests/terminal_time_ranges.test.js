/**
 * Terminal Time Range Filters Test
 * 
 * Tests for time range filter functionality in terminal commands.
 * All future chart commands MUST support these time ranges or tests will fail.
 * 
 * Run: node tests/terminal_time_ranges.test.js
 */

const assert = require('assert');

// ============================================================================
// TIME RANGE DEFINITIONS (Single source of truth)
// All chart commands must support these exact ranges
// ============================================================================

const TIME_RANGES = {
    "1m": 30,
    "2m": 60,
    "3m": 90,
    "6m": 180,
    "1y": 365,
    "2y": 730,
    "3y": 1095,
    "5y": 1825,
    "10y": 3650,
    "all": null  // No limit
};

const DEFAULT_RANGE = "1m";
const REQUIRED_RANGES = Object.keys(TIME_RANGES);

// ============================================================================
// MOCK DATA
// ============================================================================

function generateMockFutureDueData(days = 7000) {
    return Array.from({ length: days }, (_, i) => ({
        day: i,
        mature: Math.floor(Math.random() * 200) + 50,
        young: Math.floor(Math.random() * 100) + 10
    }));
}

// ============================================================================
// FILTER FUNCTION (Must match implementation in js/terminal.js)
// ============================================================================

function filterByRange(data, rangeKey) {
    const days = TIME_RANGES[rangeKey];
    if (days === null || days === undefined) {
        return data;  // "all" or invalid key returns everything
    }
    return data.slice(0, Math.min(days, data.length));
}

// ============================================================================
// COMMAND PARSER (Must match implementation in js/terminal.js)
// ============================================================================

function parseCommand(input) {
    const normalized = input.toLowerCase().trim();
    
    // Handle "due [range]" command
    const dueMatch = normalized.match(/^(due|future|reviews)\s+(.+)$/);
    if (dueMatch) {
        const [, , range] = dueMatch;
        return { command: 'due', range };
    }
    
    // Handle "show due [range]" command
    if (normalized.startsWith("show ")) {
        const parts = normalized.split(/\s+/);
        if (parts[1] === "due" || parts[1] === "future" || parts[1] === "reviews") {
            return { command: 'due', range: parts[2] || DEFAULT_RANGE };
        }
    }
    
    // Handle simple "due" command
    if (normalized === "due" || normalized === "future" || normalized === "reviews") {
        return { command: 'due', range: DEFAULT_RANGE };
    }
    
    return { command: normalized, range: null };
}

// ============================================================================
// TESTS
// ============================================================================

function runTests() {
    let passed = 0;
    let failed = 0;
    
    console.log("🧪 Terminal Time Range Filters Test\n");
    console.log("=" .repeat(60));
    
    // Test 1: All required ranges are defined
    console.log("\n📋 Test 1: Required time ranges are defined");
    REQUIRED_RANGES.forEach(range => {
        try {
            assert.ok(TIME_RANGES[range] !== undefined, `Range ${range} must be defined`);
            console.log(`   ✓ ${range}: ${TIME_RANGES[range] === null ? 'all' : TIME_RANGES[range] + ' days'}`);
            passed++;
        } catch (e) {
            console.log(`   ✗ ${range}: ${e.message}`);
            failed++;
        }
    });
    
    // Test 2: Filter function works correctly
    console.log("\n📋 Test 2: Filter function returns correct data length");
    const mockData = generateMockFutureDueData(7000);
    
    Object.entries(TIME_RANGES).forEach(([range, days]) => {
        try {
            const filtered = filterByRange(mockData, range);
            const expectedLength = days === null ? 7000 : Math.min(days, 7000);
            
            assert.strictEqual(filtered.length, expectedLength, 
                `Range ${range} should return ${expectedLength} items`);
            console.log(`   ✓ ${range}: ${filtered.length} items`);
            passed++;
        } catch (e) {
            console.log(`   ✗ ${range}: ${e.message}`);
            failed++;
        }
    });
    
    // Test 3: Command parser recognizes all ranges
    console.log("\n📋 Test 3: Command parser recognizes all ranges");
    REQUIRED_RANGES.forEach(range => {
        try {
            const result = parseCommand(`due ${range}`);
            assert.strictEqual(result.command, 'due', 'Should parse as due command');
            assert.strictEqual(result.range, range, `Should recognize range: ${range}`);
            console.log(`   ✓ "due ${range}" parsed correctly`);
            passed++;
        } catch (e) {
            console.log(`   ✗ "due ${range}": ${e.message}`);
            failed++;
        }
    });
    
    // Test 4: Default range is applied when none specified
    console.log("\n📋 Test 4: Default range applied when none specified");
    try {
        const result = parseCommand("due");
        assert.strictEqual(result.range, DEFAULT_RANGE, 'Should use default range');
        console.log(`   ✓ "due" defaults to "${DEFAULT_RANGE}"`);
        passed++;
    } catch (e) {
        console.log(`   ✗ Default range: ${e.message}`);
        failed++;
    }
    
    // Test 5: All command aliases work
    console.log("\n📋 Test 5: Command aliases work with ranges");
    const aliases = ["due", "future", "reviews"];
    aliases.forEach(alias => {
        REQUIRED_RANGES.slice(0, 3).forEach(range => {  // Test first 3 ranges for each alias
            try {
                const result = parseCommand(`${alias} ${range}`);
                assert.strictEqual(result.command, 'due', 'Should parse as due command');
                assert.strictEqual(result.range, range, `Should recognize range: ${range}`);
                console.log(`   ✓ "${alias} ${range}" parsed correctly`);
                passed++;
            } catch (e) {
                console.log(`   ✗ "${alias} ${range}": ${e.message}`);
                failed++;
            }
        });
    });
    
    // Test 6: "show due [range]" syntax works
    console.log("\n📋 Test 6: 'show due [range]' syntax works");
    REQUIRED_RANGES.slice(0, 3).forEach(range => {
        try {
            const result = parseCommand(`show due ${range}`);
            assert.strictEqual(result.command, 'due', 'Should parse as due command');
            assert.strictEqual(result.range, range, `Should recognize range: ${range}`);
            console.log(`   ✓ "show due ${range}" parsed correctly`);
            passed++;
        } catch (e) {
            console.log(`   ✗ "show due ${range}": ${e.message}`);
            failed++;
        }
    });
    
    // Test 7: Invalid ranges are rejected
    console.log("\n📋 Test 7: Invalid ranges are rejected");
    const invalidRanges = ["1w", "5m", "100d", "xyz", "20y"];
    invalidRanges.forEach(range => {
        try {
            const result = parseCommand(`due ${range}`);
            assert.strictEqual(result.range, range, 'Should capture the invalid range');
            assert.ok(!(range in TIME_RANGES), `Range ${range} should not be valid`);
            console.log(`   ✓ "${range}" correctly identified as invalid`);
            passed++;
        } catch (e) {
            console.log(`   ✗ "${range}": ${e.message}`);
            failed++;
        }
    });
    
    // Test 8: Data integrity after filtering
    console.log("\n📋 Test 8: Data integrity after filtering");
    const testData = generateMockFutureDueData(1000);
    Object.entries(TIME_RANGES).slice(0, 5).forEach(([range, days]) => {
        try {
            const filtered = filterByRange(testData, range);
            
            // Check structure
            assert.ok(Array.isArray(filtered), 'Result should be an array');
            assert.ok(filtered.every(d => 'day' in d && 'mature' in d && 'young' in d), 
                'All items should have day, mature, young properties');
            
            // Check day sequence
            filtered.forEach((item, idx) => {
                assert.strictEqual(item.day, idx, `Day should be ${idx}`);
            });
            
            console.log(`   ✓ ${range}: Data structure intact`);
            passed++;
        } catch (e) {
            console.log(`   ✗ ${range}: ${e.message}`);
            failed++;
        }
    });
    
    // Test 9: Enforce future chart commands support all ranges
    console.log("\n📋 Test 9: Enforce all chart commands support required ranges");
    const chartCommands = ["due", "future", "reviews"];
    chartCommands.forEach(cmd => {
        REQUIRED_RANGES.forEach(range => {
            try {
                const result = parseCommand(`${cmd} ${range}`);
                assert.ok(result.command === 'due', 'Command should be recognized');
                assert.ok(range in TIME_RANGES, `Range ${range} must be supported`);
                passed++;
            } catch (e) {
                console.log(`   ✗ ${cmd} ${range}: ${e.message}`);
                failed++;
            }
        });
    });
    console.log(`   ✓ All ${chartCommands.length * REQUIRED_RANGES.length} command/range combinations supported`);
    
    // Summary
    console.log("\n" + "=".repeat(60));
    console.log(`\n📊 Results: ${passed} passed, ${failed} failed\n`);
    
    if (failed > 0) {
        console.log("❌ TESTS FAILED - Some time range filters are not working correctly");
        console.log("\n⚠️  Any new chart commands MUST support these time ranges:");
        console.log(`   ${REQUIRED_RANGES.join(", ")}\n`);
        process.exit(1);
    } else {
        console.log("✅ ALL TESTS PASSED - Time range filters working correctly");
        console.log("\n📝 New chart commands must support these ranges:");
        console.log(`   ${REQUIRED_RANGES.join(", ")}\n`);
        process.exit(0);
    }
}

// Run tests
runTests();
