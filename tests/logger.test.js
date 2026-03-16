import assert from "assert";
import { isDevelopment, logger } from "../js/utils/logger.js";

function runTests() {
  let passed = 0;
  let failed = 0;

  console.log("🧪 Logger Utility Tests\n");
  console.log("=".repeat(60));

  const runTest = (name, testFn) => {
    console.log(`\n📋 Test: ${name}`);
    try {
      testFn();
      console.log(`   ✓ ${name}`);
      passed++;
    } catch (e) {
      console.log(`   ✗ ${e.message}`);
      failed++;
    }
  };

  runTest("isDevelopment checks process.env by default in node tests", () => {
    // We are running in node, process is defined, process.env is defined
    const oldNodeEnv = process.env.NODE_ENV;
    try {
      process.env.NODE_ENV = "production";
      assert.strictEqual(isDevelopment(), false);

      process.env.NODE_ENV = "development";
      assert.strictEqual(isDevelopment(), true);
    } finally {
      process.env.NODE_ENV = oldNodeEnv;
    }
  });

  runTest("logger methods call console methods when in development", () => {
    const oldNodeEnv = process.env.NODE_ENV;

    // Mock console to track calls
    const originalLog = console.log;
    const originalWarn = console.warn;
    const originalError = console.error;

    let logCalled = false;
    let warnCalled = false;
    let errorCalled = false;

    console.log = () => {
      logCalled = true;
    };
    console.warn = () => {
      warnCalled = true;
    };
    console.error = () => {
      errorCalled = true;
    };

    try {
      process.env.NODE_ENV = "development";

      logger.log("test");
      logger.warn("test");
      logger.error("test");

      assert.strictEqual(logCalled, true);
      assert.strictEqual(warnCalled, true);
      assert.strictEqual(errorCalled, true);

      logCalled = false;
      warnCalled = false;
      errorCalled = false;

      process.env.NODE_ENV = "production";

      logger.log("test");
      logger.warn("test");
      logger.error("test");

      assert.strictEqual(logCalled, false);
      assert.strictEqual(warnCalled, false);
      assert.strictEqual(errorCalled, false);
    } finally {
      process.env.NODE_ENV = oldNodeEnv;
      // Restore console
      console.log = originalLog;
      console.warn = originalWarn;
      console.error = originalError;
    }
  });

  // Summary
  console.log("\n" + "=".repeat(60));
  console.log(`\n📊 Results: ${passed} passed, ${failed} failed\n`);

  if (failed > 0) {
    console.log("❌ TESTS FAILED - Logger utility has issues\n");
    process.exit(1);
  } else {
    console.log("✅ ALL TESTS PASSED - Logger utility working correctly");
  }
}

runTests();
