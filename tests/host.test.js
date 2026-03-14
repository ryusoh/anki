import assert from "assert";
import { isLocalhost } from "../js/utils/host.js";

function runTests() {
  let passed = 0;
  let failed = 0;

  console.log("🧪 Host Utility Tests\n");
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

  runTest("Returns false for empty hostname", () => {
    assert.strictEqual(isLocalhost(""), false);
    assert.strictEqual(isLocalhost(null), false);
    assert.strictEqual(isLocalhost(undefined), false);
  });

  runTest("Identifies common loopback hostnames", () => {
    assert.strictEqual(isLocalhost("localhost"), true);
    assert.strictEqual(isLocalhost("127.0.0.1"), true);
    assert.strictEqual(isLocalhost("::1"), true);
    assert.strictEqual(isLocalhost("0.0.0.0"), true);
  });

  runTest("Identifies .local domains", () => {
    assert.strictEqual(isLocalhost("my-computer.local"), true);
    assert.strictEqual(isLocalhost("test.local"), true);
  });

  runTest("Identifies private IPv4 ranges", () => {
    // 10.x.x.x
    assert.strictEqual(isLocalhost("10.0.0.1"), true);
    assert.strictEqual(isLocalhost("10.255.255.255"), true);

    // 172.16.x.x to 172.31.x.x
    assert.strictEqual(isLocalhost("172.16.0.1"), true);
    assert.strictEqual(isLocalhost("172.31.255.255"), true);
    assert.strictEqual(isLocalhost("172.15.0.1"), false, "Outside private range");
    assert.strictEqual(isLocalhost("172.32.0.1"), false, "Outside private range");

    // 192.168.x.x
    assert.strictEqual(isLocalhost("192.168.0.1"), true);
    assert.strictEqual(isLocalhost("192.168.255.255"), true);
    assert.strictEqual(isLocalhost("192.169.0.1"), false, "Outside private range");
  });

  runTest("Returns false for public hostnames", () => {
    assert.strictEqual(isLocalhost("example.com"), false);
    assert.strictEqual(isLocalhost("google.com"), false);
    assert.strictEqual(isLocalhost("8.8.8.8"), false);
    assert.strictEqual(isLocalhost("1.1.1.1"), false);
  });

  // Summary
  console.log("\n" + "=".repeat(60));
  console.log(`\n📊 Results: ${passed} passed, ${failed} failed\n`);

  if (failed > 0) {
    console.log("❌ TESTS FAILED - Host utility has issues\n");
    process.exit(1);
  } else {
    console.log("✅ ALL TESTS PASSED - Host utility working correctly");
    process.exit(0);
  }
}

runTests();
