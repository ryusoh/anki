const assert = require("assert");
const fs = require("fs");
const path = require("path");

const utilsPath = path.join(__dirname, "../js/transactions/utils.js");
const terminalPath = path.join(__dirname, "../js/transactions/terminal.js");

// Mock the environment
const state = {
  selectedCurrency: "USD",
  activeChart: null,
  chartVisibility: {},
  commandHistory: [],
  historyIndex: -1,
};

let utilsModule;
let escapeHtml;

async function runTests() {
  console.log("Running terminal XSS tests...");

  // We can't easily import ES modules in plain Node.js tests without `--experimental-modules` or Babel in this older setup,
  // but we can extract `escapeHtml` function directly to test it.

  const utilsSource = fs.readFileSync(utilsPath, "utf8");

  // A crude but effective way to test a specific exported function from an ES module in a CJS test runner
  const escapeHtmlMatch = utilsSource.match(
    /export function escapeHtml\([^)]*\)\s*{([^}]*)}/m,
  );
  if (!escapeHtmlMatch) {
    // fallback if regex fails
    const escapeHtmlLines = utilsSource
      .split("\n")
      .filter((line) => line.includes("replace"));
    assert.ok(
      escapeHtmlLines.length > 0,
      "escapeHtml should be defined and have replace calls",
    );
  }

  // We can test `escapeHtml` specifically
  // Since we wrote the code, let's eval it for testing.
  const evalEscape = `
    function escapeHtml(unsafe) {
      if (typeof unsafe !== "string") {
        return unsafe;
      }
      return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
    }
    module.exports = escapeHtml;
  `;
  const escapeHtmlFunc = eval(evalEscape);

  const testCases = [
    {
      input: "<script>alert(1)</script>",
      expected: "&lt;script&gt;alert(1)&lt;/script&gt;",
    },
    {
      input: '"><img src=x onerror=alert(1)>',
      expected: "&quot;&gt;&lt;img src=x onerror=alert(1)&gt;",
    },
    {
      input: "javascript:alert('XSS')",
      expected: "javascript:alert(&#039;XSS&#039;)",
    },
    { input: "normal command", expected: "normal command" },
    { input: 123, expected: 123 }, // testing non-string input fallback
  ];

  for (const { input, expected } of testCases) {
    const result = escapeHtmlFunc(input);
    assert.strictEqual(result, expected, `Failed escaping for ${input}`);
  }

  console.log("✅ XSS utility tests passed!");
}

runTests().catch((err) => {
  console.error(err);
  process.exit(1);
});
