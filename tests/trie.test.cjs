/**
 * Command Trie Autocomplete Test
 * Tests trie-based command validation and autocomplete
 *
 * Run: node tests/trie.test.js
 */

const assert = require("assert");

// Mock the trie module (since we're testing in Node.js)
const { TrieNode, CommandTrie, createCommandTrie } = (() => {
  // Inline the trie implementation for testing
  class TrieNode {
    constructor() {
      this.children = {};
      this.isEndOfCommand = false;
      this.command = null;
    }
  }

  class CommandTrie {
    constructor() {
      this.root = new TrieNode();
      this.commands = new Set();
    }

    insert(command) {
      const normalized = command.toLowerCase().trim();
      if (!normalized) return;

      let node = this.root;

      // Insert character by character for proper prefix matching
      for (const char of normalized) {
        if (!node.children[char]) {
          node.children[char] = new TrieNode();
        }
        node = node.children[char];
      }

      node.isEndOfCommand = true;
      node.command = normalized;
      this.commands.add(normalized);
    }

    insertAll(commands) {
      commands.forEach((cmd) => this.insert(cmd));
    }

    search(command) {
      const normalized = command.toLowerCase().trim();
      return this.commands.has(normalized);
    }

    startsWith(prefix) {
      const normalized = prefix.toLowerCase().trim();
      if (!normalized) return true;

      let node = this.root;
      for (const char of normalized) {
        if (!node.children[char]) {
          return false;
        }
        node = node.children[char];
      }
      return true;
    }

    autocomplete(prefix, limit = 10) {
      const normalized = prefix.toLowerCase().trim();
      if (!normalized) {
        return Array.from(this.commands).slice(0, limit);
      }

      let node = this.root;
      for (const char of normalized) {
        if (!node.children[char]) {
          return [];
        }
        node = node.children[char];
      }

      const suggestions = [];
      this._collectCommands(node, normalized, suggestions, limit);
      return suggestions;
    }

    _collectCommands(node, prefix, results, limit) {
      if (results.length >= limit) return;

      if (node.isEndOfCommand) {
        results.push(node.command);
      }

      for (const [char, childNode] of Object.entries(node.children)) {
        this._collectCommands(childNode, prefix + char, results, limit);
      }
    }

    validate(command) {
      const normalized = command.toLowerCase().trim();

      if (this.search(normalized)) {
        return { valid: true, suggestions: [] };
      }

      if (this.startsWith(normalized)) {
        const suggestions = this.autocomplete(normalized, 5);
        return {
          valid: false,
          suggestions,
          isPartial: true,
        };
      }

      return {
        valid: false,
        suggestions: [],
        isPartial: false,
      };
    }

    getAllCommands() {
      return Array.from(this.commands);
    }

    size() {
      return this.commands.size;
    }

    clear() {
      this.root = new TrieNode();
      this.commands.clear();
    }
  }

  function createCommandTrie() {
    const trie = new CommandTrie();

    trie.insertAll([
      // Base commands with abbreviations
      "help",
      "h",
      "?",
      "charts",
      "list",
      "clear",
      "cls",
      "c",
      "plot",
      "p",
      "plot due",
      "pd",
      "plot reviews",
      "pr",
      "due",
      "d",
      "future",
      "f",
      "reviews",
      "r",
      "show",
      "s",
      "show due",
      "sd",
      "show reviews",
      "sr",
      // Range shortcuts
      "1m",
      "2m",
      "3m",
      "6m",
      "1y",
      "2y",
      "3y",
      "5y",
      "10y",
      "all",
    ]);

    // Full plot commands with ranges
    const ranges = [
      "1m",
      "2m",
      "3m",
      "6m",
      "1y",
      "2y",
      "3y",
      "5y",
      "10y",
      "all",
    ];
    ranges.forEach((range) => {
      trie.insert(`plot due ${range}`);
      trie.insert(`plot reviews ${range}`);
      trie.insert(`show due ${range}`);
      trie.insert(`show reviews ${range}`);
    });

    return trie;
  }

  return { TrieNode, CommandTrie, createCommandTrie };
})();

// ============================================================================
// TESTS
// ============================================================================

async function runTests() {
  const { TrieNode, CommandTrie, createCommandTrie } = await import("../js/utils/trie.js");
  let passed = 0;
  let failed = 0;
  let trie;

  console.log("🧪 Command Trie Autocomplete Test\n");
  console.log("=".repeat(60));

  // Setup
  console.log("\n📋 Setup: Create command trie");
  try {
    trie = createCommandTrie();
    assert.ok(trie.size() > 0, "Trie should have commands");
    console.log(`   ✓ Trie created with ${trie.size()} commands`);
    passed++;
  } catch (e) {
    console.log(`   ✗ Setup failed: ${e.message}`);
    failed++;
  }

  // Test 1: Valid commands are recognized
  console.log("\n📋 Test 1: Valid commands are recognized");
  const validCommands = [
    "help",
    "plot due",
    "plot reviews 3m",
    "due",
    "reviews",
    "1m",
    "all",
  ];
  validCommands.forEach((cmd) => {
    try {
      const result = trie.validate(cmd);
      assert.strictEqual(result.valid, true, `${cmd} should be valid`);
      console.log(`   ✓ "${cmd}" → valid`);
      passed++;
    } catch (e) {
      console.log(`   ✗ "${cmd}": ${e.message}`);
      failed++;
    }
  });

  // Test 2: Invalid commands are rejected
  console.log("\n📋 Test 2: Invalid commands are rejected (not in trie)");
  const invalidCommands = [
    "unknown",
    "foo bar",
    "plot foo",
    "invalid123",
    "xyz",
  ];
  invalidCommands.forEach((cmd) => {
    try {
      const result = trie.validate(cmd);
      assert.strictEqual(result.valid, false, `${cmd} should be invalid`);
      assert.strictEqual(
        result.isPartial,
        false,
        `${cmd} should not be partial match`,
      );
      assert.strictEqual(
        result.suggestions.length,
        0,
        `${cmd} should have no suggestions`,
      );
      console.log(`   ✓ "${cmd}" → rejected (not in trie)`);
      passed++;
    } catch (e) {
      console.log(`   ✗ "${cmd}": ${e.message}`);
      failed++;
    }
  });

  // Test 3: Partial matches return suggestions
  console.log("\n📋 Test 3: Partial matches return suggestions");
  const partialTests = [
    { prefix: "pl", expectedContains: "plot" },
    { prefix: "plot d", expectedContains: "plot due" },
    { prefix: "plot r", expectedContains: "plot reviews" },
    { prefix: "1", expectedContains: "1m" },
  ];
  partialTests.forEach(({ prefix, expectedContains }) => {
    try {
      const result = trie.validate(prefix);
      assert.strictEqual(
        result.valid,
        false,
        `${prefix} should not be exact match`,
      );
      assert.strictEqual(
        result.isPartial,
        true,
        `${prefix} should be partial match`,
      );
      assert.ok(
        result.suggestions.length > 0,
        `${prefix} should have suggestions`,
      );
      assert.ok(
        result.suggestions.some((s) => s.includes(expectedContains)),
        `Suggestions should contain "${expectedContains}"`,
      );
      console.log(
        `   ✓ "${prefix}" → ${result.suggestions.length} suggestions`,
      );
      passed++;
    } catch (e) {
      console.log(`   ✗ "${prefix}": ${e.message}`);
      failed++;
    }
  });

  // Test 4: Autocomplete returns correct suggestions
  console.log("\n📋 Test 4: Autocomplete returns correct suggestions");
  const autocompleteTests = [
    { prefix: "plot", minSuggestions: 2 },
    { prefix: "plot due", minSuggestions: 5 },
    { prefix: "show", minSuggestions: 2 },
    { prefix: "1", minSuggestions: 1 },
  ];
  autocompleteTests.forEach(({ prefix, minSuggestions }) => {
    try {
      const suggestions = trie.autocomplete(prefix);
      assert.ok(
        suggestions.length >= minSuggestions,
        `${prefix} should have at least ${minSuggestions} suggestions`,
      );
      console.log(`   ✓ "${prefix}" → ${suggestions.length} suggestions`);
      passed++;
    } catch (e) {
      console.log(`   ✗ "${prefix}": ${e.message}`);
      failed++;
    }
  });

  // Test 5: Future-proof - detect new commands not in trie
  console.log("\n📋 Test 5: Future-proof - detect unknown commands");
  const futureCommands = [
    "plot newchart",
    "analyze",
    "stats",
    "export data",
    "import",
  ];
  futureCommands.forEach((cmd) => {
    try {
      const result = trie.validate(cmd);
      assert.strictEqual(
        result.valid,
        false,
        `${cmd} should be invalid (not registered)`,
      );
      assert.strictEqual(
        result.isPartial,
        false,
        `${cmd} should not be partial match`,
      );
      console.log(`   ✓ "${cmd}" → rejected (future command not registered)`);
      passed++;
    } catch (e) {
      console.log(`   ✗ "${cmd}": ${e.message}`);
      failed++;
    }
  });

  // Test 6: Case insensitive
  console.log("\n📋 Test 6: Case insensitive matching");
  const caseTests = ["HELP", "Plot Due", "REVIEWS", "pLoT dUe 3M"];
  caseTests.forEach((cmd) => {
    try {
      const normalized = cmd.toLowerCase();
      const result = trie.validate(cmd);
      const expectedResult = trie.search(normalized);
      assert.strictEqual(
        result.valid,
        expectedResult,
        `${cmd} should match case-insensitively`,
      );
      console.log(`   ✓ "${cmd}" → case insensitive match`);
      passed++;
    } catch (e) {
      console.log(`   ✗ "${cmd}": ${e.message}`);
      failed++;
    }
  });

  // Test 7: Empty/whitespace handling
  console.log("\n📋 Test 7: Empty/whitespace handling");
  try {
    const emptyResult = trie.validate("");
    const spaceResult = trie.validate("   ");
    assert.ok(
      emptyResult.valid || emptyResult.suggestions.length > 0,
      "Empty should return all commands",
    );
    assert.ok(
      spaceResult.valid || spaceResult.suggestions.length > 0,
      "Whitespace should return all commands",
    );
    console.log("   ✓ Empty/whitespace handled correctly");
    passed++;
  } catch (e) {
    console.log(`   ✗ Empty/whitespace: ${e.message}`);
    failed++;
  }

  // Test 8: Trie size and getAllCommands
  console.log("\n📋 Test 8: Trie metadata");
  try {
    const allCommands = trie.getAllCommands();
    assert.strictEqual(
      allCommands.length,
      trie.size(),
      "getAllCommands should match size",
    );
    assert.ok(allCommands.includes("plot due"), "Should include plot due");
    assert.ok(allCommands.includes("reviews"), "Should include reviews");
    assert.ok(allCommands.includes("1m"), "Should include 1m");
    console.log(`   ✓ Trie has ${trie.size()} commands`);
    passed++;
  } catch (e) {
    console.log(`   ✗ Trie metadata: ${e.message}`);
    failed++;
  }

  // Test 9: Clear and re-populate
  console.log("\n📋 Test 9: Clear and re-populate");
  try {
    const initialSize = trie.size();
    trie.clear();
    assert.strictEqual(trie.size(), 0, "Clear should empty trie");

    trie.insert("test command");
    assert.strictEqual(trie.size(), 1, "Should have 1 command after insert");
    assert.strictEqual(
      trie.search("test command"),
      true,
      "Should find inserted command",
    );

    // Restore
    trie.clear();
    trie = createCommandTrie();
    console.log("   ✓ Clear and re-populate works");
    passed++;
  } catch (e) {
    console.log(`   ✗ Clear/re-populate: ${e.message}`);
    failed++;
  }

  // Test 10: Validate all registered commands
  console.log("\n📋 Test 10: Validate all registered commands");
  try {
    const allCommands = trie.getAllCommands();
    let validCount = 0;
    allCommands.forEach((cmd) => {
      const result = trie.validate(cmd);
      if (result.valid) validCount++;
    });
    assert.strictEqual(
      validCount,
      allCommands.length,
      "All registered commands should be valid",
    );
    console.log(`   ✓ All ${allCommands.length} commands validated`);
    passed++;
  } catch (e) {
    console.log(`   ✗ Validate all: ${e.message}`);
    failed++;
  }

  // Test 11: Abbreviations work
  console.log("\n📋 Test 11: Command abbreviations");
  const abbreviations = [
    { abbrev: "h", expands: "help" },
    { abbrev: "p", expands: "plot" },
    { abbrev: "pd", expands: "plot due" },
    { abbrev: "pr", expands: "plot reviews" },
    { abbrev: "c", expands: "clear" },
    { abbrev: "d", expands: "due" },
    { abbrev: "r", expands: "reviews" },
    { abbrev: "s", expands: "show" },
  ];
  abbreviations.forEach(({ abbrev, expands }) => {
    try {
      const result = trie.validate(abbrev);
      assert.strictEqual(result.valid, true, `${abbrev} should be valid`);
      console.log(`   ✓ "${abbrev}" → valid (expands to ${expands})`);
      passed++;
    } catch (e) {
      console.log(`   ✗ "${abbrev}": ${e.message}`);
      failed++;
    }
  });

  // Summary
  console.log("\n" + "=".repeat(60));
  console.log(`\n📊 Results: ${passed} passed, ${failed} failed\n`);

  if (failed > 0) {
    console.log("❌ TESTS FAILED - Trie has issues");
    console.log("\n⚠️  Requirements:");
    console.log("   • Valid commands must be recognized");
    console.log("   • Invalid commands must be rejected (not in trie)");
    console.log("   • Partial matches must return suggestions");
    console.log("   • Future commands not in trie must fail validation");
    console.log();
    process.exit(1);
  } else {
    console.log("✅ ALL TESTS PASSED - Trie working correctly");
    console.log("\n📝 Verified:");
    console.log("   • Valid commands recognized");
    console.log("   • Invalid commands rejected (not in trie)");
    console.log("   • Partial matches return suggestions");
    console.log("   • Future-proof: unknown commands detected");
    console.log("   • Case insensitive matching");
    console.log("   • Autocomplete works correctly");
    console.log();
    process.exit(0);
  }
}

// Run tests
runTests();
