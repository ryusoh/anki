const assert = require("assert");

async function runTests() {
  let passed = 0;
  let failed = 0;

  console.log("[TEST] Host Utils Tests\n");
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

  const { isLocalhost } = await import("../js/utils/host.js");

  runTest("isLocalhost basic functionality", () => {
    assert.strictEqual(isLocalhost("localhost"), true);
    assert.strictEqual(isLocalhost("127.0.0.1"), true);
    assert.strictEqual(isLocalhost("::1"), true);
    assert.strictEqual(isLocalhost("0.0.0.0"), true);
    assert.strictEqual(isLocalhost("google.com"), false);
    assert.strictEqual(isLocalhost(""), false);
    assert.strictEqual(isLocalhost(null), false);
    assert.strictEqual(isLocalhost(undefined), false);

    assert.strictEqual(isLocalhost("my-macbook.local"), true);
    assert.strictEqual(isLocalhost("test.local"), true);
    assert.strictEqual(isLocalhost("local.com"), false);

    assert.strictEqual(isLocalhost("192.168.1.1"), true);
    assert.strictEqual(isLocalhost("192.168.0.255"), true);
    assert.strictEqual(isLocalhost("10.0.0.1"), true);
    assert.strictEqual(isLocalhost("172.16.0.1"), true);
    assert.strictEqual(isLocalhost("172.31.255.255"), true);
    assert.strictEqual(isLocalhost("172.32.0.1"), false);
    assert.strictEqual(isLocalhost("172.15.0.1"), false);
    assert.strictEqual(isLocalhost("8.8.8.8"), false);
    assert.strictEqual(isLocalhost("1.1.1.1"), false);
  });

  console.log("\n" + "=".repeat(60));
  console.log(`\n[SUMMARY] Results: ${passed} passed, ${failed} failed\n`);

  if (failed > 0) {
    process.exitCode = 1;
  }
}

runTests().catch((err) => {
  console.error(err);
  process.exit(1);
});
