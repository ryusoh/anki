import assert from "assert";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { JSDOM } from "jsdom";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.join(__dirname, "..");

async function runTests() {
  let passed = 0;
  let failed = 0;

  console.log("[TEST] Terminal Style Regression Tests\n");
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

  // Helper to get CSS rules for a selector
  const getRulesForSelector = (dom, selector) => {
    const rules = [];
    for (const sheet of dom.window.document.styleSheets) {
      try {
        for (const rule of sheet.cssRules) {
          if (rule.selectorText && rule.selectorText.includes(selector)) {
            rules.push(rule);
          }
        }
      } catch (e) {
        // Some rules might not be accessible
      }
    }
    return rules;
  };

  runTest("Terminal input focus should not have yellow outline/border/shadow", () => {
    const cssContent = fs.readFileSync(
      path.join(rootDir, "css/terminal/terminal.css"),
      "utf8",
    );
    const baseCssContent = fs.readFileSync(
      path.join(rootDir, "css/terminal/base.css"),
      "utf8",
    );

    // Create a JSDOM environment with the CSS
    const dom = new JSDOM(`
      <!DOCTYPE html>
      <html>
        <head>
          <style>${baseCssContent}</style>
          <style>${cssContent}</style>
        </head>
        <body>
          <input id="terminalInput" class="terminal-input" />
        </body>
      </html>
    `, {
      resources: "usable",
      runScripts: "dangerously"
    });

    // We can't easily test computed styles of pseudo-classes like :focus-visible in JSDOM
    // but we can inspect the raw CSS rules we injected.
    
    const focusRules = getRulesForSelector(dom, ".terminal-input:focus");
    const focusVisibleRules = getRulesForSelector(dom, ".terminal-input:focus-visible");
    
    assert.ok(focusRules.length > 0 || focusVisibleRules.length > 0, "Focus rules for .terminal-input should exist");
    
    // Check that at least one of these rules sets outline to none
    let hasOutlineNone = false;
    let hasBoxShadowNone = false;
    let hasBorderNone = false;
    
    const allFocusRules = [...focusRules, ...focusVisibleRules];
    
    for (const rule of allFocusRules) {
      const cssText = rule.cssText.toLowerCase();
      if (rule.style.outline === "none" || cssText.includes("outline: none")) hasOutlineNone = true;
      if (rule.style.boxShadow === "none" || cssText.includes("box-shadow: none")) hasBoxShadowNone = true;
      // JSDOM seems to normalize 'border: none !important' to 'border: medium !important' or similar in cssText
      if (rule.style.border === "none" || cssText.includes("border: none") || cssText.includes("border-width: 0px") || cssText.includes("border-top-style: none") || cssText.includes("border: medium !important")) hasBorderNone = true;
    }
    
    assert.strictEqual(hasOutlineNone, true, "Should have outline: none for focused terminal input");
    assert.strictEqual(hasBoxShadowNone, true, "Should have box-shadow: none for focused terminal input");
    assert.strictEqual(hasBorderNone, true, "Should have border: none for focused terminal input");
  });

  // Summary
  console.log("\n" + "=".repeat(60));
  console.log(`\n[SUMMARY] Results: ${passed} passed, ${failed} failed\n`);

  if (failed > 0) {
    console.log("[ERROR] TESTS FAILED - Terminal style regression detected\n");
    process.exitCode = 1;
  } else {
    console.log(
      "[SUCCESS] ALL TESTS PASSED - Terminal styles are correct",
    );
  }
}

runTests().catch((err) => {
  console.error(err);
  process.exit(1);
});
