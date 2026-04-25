const assert = require("assert");

async function runTests() {
  let passed = 0;
  let failed = 0;

  console.log("[TEST] Config Tests\n");
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

  // Mock global window and document for getCalendarRange tests
  global.window = {
    innerWidth: 1024,
  };
  global.document = {
    querySelector: () => null,
  };

  const { getCalendarRange } = await import("../js/config.js");

  runTest("getCalendarRange without zoom, normal width", () => {
    global.window.innerWidth = 1400;
    global.document.querySelector = (selector) => {
      if (selector === ".page-center-wrapper.zoomed") return null;
      return null;
    };
    const range = getCalendarRange();
    assert.strictEqual(typeof range, "number");
  });

  runTest("getCalendarRange small width", () => {
    global.window.innerWidth = 400;
    global.document.querySelector = () => null;
    assert.strictEqual(getCalendarRange(), 1);
  });

  runTest("getCalendarRange tablet width", () => {
    global.window.innerWidth = 600;
    global.document.querySelector = () => null;
    // maxMonths = Math.floor((600*0.9)/280) = Math.floor(540/280) = 1
    assert.strictEqual(getCalendarRange(), 1);
  });

  runTest("getCalendarRange zoomed large width", () => {
    global.window.innerWidth = 1400;
    global.document.querySelector = (selector) => {
      if (selector === ".page-center-wrapper.zoomed") return true; // mock it's zoomed
      return null;
    };
    const range = getCalendarRange();
    assert.strictEqual(typeof range, "number");
  });

  runTest("getCalendarRange max 3 months", () => {
    global.window.innerWidth = 3000;
    global.document.querySelector = () => null;
    assert.strictEqual(getCalendarRange(), 3);
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
