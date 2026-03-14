import assert from "assert";
import { debounce } from "../js/utils/debounce.js";

async function runTests() {
  let passed = 0;
  let failed = 0;

  console.log("🧪 Debounce Utility Tests\n");
  console.log("=".repeat(60));

  // Test 1: Function is called after wait time
  console.log("\n📋 Test 1: Function is called after wait time");
  try {
    let callCount = 0;
    const fn = debounce(() => {
      callCount++;
    }, 50);

    fn();
    assert.strictEqual(
      callCount,
      0,
      "Function should not be called immediately",
    );

    await new Promise((resolve) => setTimeout(resolve, 100));
    assert.strictEqual(
      callCount,
      1,
      "Function should be called after wait time",
    );

    console.log("   ✓ Function is called after wait time");
    passed++;
  } catch (e) {
    console.log(`   ✗ ${e.message}`);
    failed++;
  }

  // Test 2: Multiple calls within wait time only trigger once
  console.log("\n📋 Test 2: Multiple calls within wait time only trigger once");
  try {
    let callCount = 0;
    const fn = debounce(() => {
      callCount++;
    }, 50);

    fn();
    fn();
    fn();
    assert.strictEqual(
      callCount,
      0,
      "Function should not be called immediately",
    );

    await new Promise((resolve) => setTimeout(resolve, 100));
    assert.strictEqual(
      callCount,
      1,
      "Function should only be called once after multiple rapid calls",
    );

    console.log("   ✓ Multiple calls within wait time only trigger once");
    passed++;
  } catch (e) {
    console.log(`   ✗ ${e.message}`);
    failed++;
  }

  // Test 3: Arguments are passed correctly
  console.log("\n📋 Test 3: Arguments are passed correctly");
  try {
    let argsReceived = [];
    const fn = debounce((...args) => {
      argsReceived = args;
    }, 50);

    fn(1, "test", true);

    await new Promise((resolve) => setTimeout(resolve, 100));
    assert.deepStrictEqual(
      argsReceived,
      [1, "test", true],
      "Arguments should be passed to the debounced function",
    );

    console.log("   ✓ Arguments are passed correctly");
    passed++;
  } catch (e) {
    console.log(`   ✗ ${e.message}`);
    failed++;
  }

  // Test 4: `this` context is preserved
  console.log("\n📋 Test 4: `this` context is preserved");
  try {
    const obj = {
      val: 42,
      fn: debounce(function () {
        this.called = true;
      }, 50),
    };

    obj.fn();

    await new Promise((resolve) => setTimeout(resolve, 100));
    assert.strictEqual(obj.called, true, "`this` context should be preserved");

    console.log("   ✓ `this` context is preserved");
    passed++;
  } catch (e) {
    console.log(`   ✗ ${e.message}`);
    failed++;
  }

  // Summary
  console.log("\n" + "=".repeat(60));
  console.log(`\n📊 Results: ${passed} passed, ${failed} failed\n`);

  if (failed > 0) {
    console.log("❌ TESTS FAILED - Debounce utility has issues\n");
    process.exit(1);
  } else {
    console.log("✅ ALL TESTS PASSED - Debounce utility working correctly");
    process.exit(0);
  }
}

runTests();
