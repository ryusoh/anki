import assert from "assert";
import { isDevelopment, logger } from "../js/utils/logger.js";

function runTests() {
  let passed = 0;
  let failed = 0;

  console.log("[TEST] Logger Utility Tests\n");
  console.log("=".repeat(60));

  const runTest = (name, testFn) => {
    console.log(`\n[CASE] Test: ${name}`);
    try {
      testFn();
      console.log(`   [PASS] ${name}`);
      passed++;
    } catch (e) {
      console.log(`   [FAIL] ${e.message}`);
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

  runTest("isDevelopment checks window.location.hostname in browser", () => {
    const oldProcess = global.process;

    // Temporarily hide process to trigger window branch
    global.process = undefined;

    const oldWindow = global.window;

    try {
      // Mock window
      global.window = {
        location: {
          hostname: "localhost"
        }
      };
      assert.strictEqual(isDevelopment(), true);

      global.window.location.hostname = "127.0.0.1";
      assert.strictEqual(isDevelopment(), true);

      global.window.location.hostname = "dev.example.com";
      assert.strictEqual(isDevelopment(), true);

      global.window.location.hostname = "test.example.com";
      assert.strictEqual(isDevelopment(), true);

      global.window.location.hostname = "staging.example.com";
      assert.strictEqual(isDevelopment(), true);

      global.window.location.hostname = "example.com";
      assert.strictEqual(isDevelopment(), false);

      global.window.location.hostname = "app.prod.com";
      assert.strictEqual(isDevelopment(), false);

    } finally {
      global.window = oldWindow;
      global.process = oldProcess;
    }
  });

  runTest("isDevelopment defaults to true if neither process nor window exists", () => {
    const oldProcess = global.process;
    const oldWindow = global.window;

    try {
      global.process = undefined;
      global.window = undefined;

      assert.strictEqual(isDevelopment(), true);
    } finally {
      global.process = oldProcess;
      global.window = oldWindow;
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
  console.log(`\n[SUMMARY] Results: ${passed} passed, ${failed} failed\n`);

  if (failed > 0) {
    console.log("[ERROR] TESTS FAILED - Logger utility has issues\n");
    process.exit(1);
  } else {
    console.log("[SUCCESS] ALL TESTS PASSED - Logger utility working correctly");
  }
}

runTests();
