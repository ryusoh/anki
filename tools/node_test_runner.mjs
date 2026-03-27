import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';
import os from 'os';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// ANSI Color Codes
const RESET = '\x1b[0m';
const BOLD = '\x1b[1m';
const GREEN = '\x1b[32m';
const RED = '\x1b[31m';
const YELLOW = '\x1b[33m';
const DIM = '\x1b[2m';
const BG_GREEN = '\x1b[42m\x1b[30m';
const BG_RED = '\x1b[41m\x1b[37m';

const tests = [
  { name: 'Debounce', path: 'tests/debounce.test.js' },
  { name: 'Formatting', path: 'tests/formatting.test.js' },
  { name: 'Logger', path: 'tests/logger.test.js' },
  { name: 'Asset Classes', path: 'tests/assetClasses.test.js' },
  { name: 'Colors', path: 'tests/colors.test.js' },
  { name: 'Easing', path: 'tests/easing.test.js' },
  { name: 'Smoothing', path: 'tests/smoothing.test.js' },
  { name: 'Host', path: 'tests/host.test.js' },
  { name: 'Date', path: 'tests/date.test.js' },
  { name: 'Handler Validation', path: 'tests/validateCommand.real.test.mjs' },
  { name: 'Handler Regression', path: 'tests/handler_regression.test.mjs' },
  { name: 'Data Files', path: 'tests/data_files.test.cjs' },
  { name: 'Time Ranges', path: 'tests/terminal_time_ranges.test.cjs' },
  { name: 'Commands', path: 'tests/commands.test.cjs' },
  { name: 'Legend', path: 'tests/legend.test.cjs' },
  { name: 'Trie', path: 'tests/trie.test.cjs' },
  { name: 'TimeRange Utils', path: 'tests/timeRange.test.cjs' },
  { name: 'Reviews', path: 'tests/reviews.test.cjs' },
  { name: 'Asset Classes', path: 'tests/assetClasses.test.js' },
  { name: 'Config Utils', path: 'tests/config.test.js' },
  { name: 'State', path: 'tests/state.test.js' },
  { name: 'Utils Format', path: 'tests/utils_format.test.js' },
  { name: 'Utils CSV', path: 'tests/utils_csv.test.js' },
  { name: 'Due', path: 'tests/due.test.cjs' }
];

async function runTest(test) {
  return new Promise((resolve) => {
    const start = Date.now();
    const child = spawn('node', [test.path]);
    
    let stdout = '';
    let stderr = '';
    
    child.stdout.on('data', (data) => { stdout += data; });
    child.stderr.on('data', (data) => { stderr += data; });
    
    child.on('close', (code) => {
      const duration = Date.now() - start;
      resolve({
        ...test,
        code,
        duration,
        stdout,
        stderr,
        success: code === 0
      });
    });
  });
}

async function main() {
  console.log(`\n${BOLD}🚀 Running Node.js Test Suite...${RESET}\n`);
  
  const results = [];
  for (const test of tests) {
    const result = await runTest(test);
    results.push(result);
    process.stdout.write(result.success ? `${GREEN}✓${RESET} ` : `${RED}✕${RESET} `);
    if (results.length % 5 === 0 || results.length === tests.length) {
      process.stdout.write('\n');
    }
  }
  
  console.log(`\n${BOLD}Test Summary:${RESET}`);
  
  let passedCount = 0;
  results.forEach(res => {
    const duration = (res.duration / 1000).toFixed(2);
    const timeStr = res.duration > 500 ? `${YELLOW}(${duration}s)${RESET}` : `${DIM}(${duration}s)${RESET}`;
    
    if (res.success) {
      console.log(`  ${BG_GREEN} PASS ${RESET} ${DIM}tests/${RESET}${BOLD}${res.path.split('/').pop()}${RESET} ${timeStr}`);
      passedCount++;
    } else {
      console.log(`  ${BG_RED} FAIL ${RESET} ${DIM}tests/${RESET}${BOLD}${res.path.split('/').pop()}${RESET} ${timeStr}`);
      console.log(`\n${RED}${BOLD}--- Failure Output ---${RESET}`);
      console.log(res.stdout || res.stderr);
      console.log(`${RED}${BOLD}----------------------${RESET}\n`);
    }
  });

  // Final Coverage Report using c8
  console.log(`\n${BOLD}Coverage Report (Real):${RESET}`);
  const testPaths = tests.map(t => t.path);
  
  // Since some modules use top-level async execution or have side-effects that interfere
  // with coverage collection in a single process, we run c8 directly on the tests using the runner.

  // Wait, no. If we just run tests individually with c8, we get correct coverage.
  // Actually, wait! The problem is that many tests mock globals in their test files (like colors.test.js mocking document).
  // When run sequentially in the same process, they pollute each other or fail.
  // We can just run the original node test runner but with c8 wrapping IT!
  // Wait, if we wrap `node_test_runner.mjs` with c8, c8 will collect coverage from child processes automatically!
  // BUT node_test_runner.mjs spawns node tests, c8 supports this if --all or proper settings are used.

  // To keep it simple, we just generate a simple test runner script that imports all original SOURCE files, NOT tests!
  // That will give us the base line, BUT coverage requires executing the code.

  // Oh, wait! c8 collects coverage from node's built in inspector.
  // By importing the test files, we run the tests.
  // The reason it's failing to get coverage for colors.js and host.js is that the test files mock globals
  // and run asynchronous code without exporting a promise.
  // To fix this, let's just make the temporary script execute them as child processes with c8!
  // Wait, `c8` can just run `node --test tests/*.js` or similar if we wanted, but we have a custom runner.

  const runnerScript = `

    const testPaths = ${JSON.stringify(testPaths)};

    // Run all tests sequentially in this process? No, we spawn them in the same process to collect coverage.
    // Actually, c8 has a programmatic API, but it's simpler to just import the source files
    // Wait, let's just import the test files sequentially and await them if possible.
    // If they execute asynchronously, we might just need to wait longer.

    // Simply run all test paths sequentially with node
    // Wait, we need them to run as child processes so they can execute cleanly.
    // However, c8 CAN capture multiple child processes by default!
    // But since the current npx c8 command runs a single temp file,
    // we can make that temp file spawn the child processes using spawnSync.
    
    import { spawnSync } from 'child_process';
    import path from 'path';

    const testFilesToRun = ${JSON.stringify(testPaths)};
    
    for (const p of testFilesToRun) {
      spawnSync(process.execPath, [path.join(process.cwd(), p)]);
    }
  `;
  const tempFile = path.join(process.cwd(), `test-runner-${Date.now()}.mjs`);
  fs.writeFileSync(tempFile, runnerScript);

  // Note: we must set clean: false or similar if we want to combine? No, running in same c8 invocation
  // will capture child processes automatically because c8 intercepts child_process.spawn
  const coverageChild = spawn('npx', ['c8', '--include=js/**', '--reporter=text', 'node', tempFile]);
  
  coverageChild.stdout.pipe(process.stdout);
  coverageChild.stderr.pipe(process.stderr);
  
  coverageChild.on('close', (code) => {
    try { fs.unlinkSync(tempFile); } catch (e) {}
    
    const totalDuration = (results.reduce((a, b) => a + b.duration, 0) / 1000).toFixed(2);
    const testsLabel = passedCount === tests.length ? `${GREEN}${passedCount} passed${RESET}` : `${RED}${tests.length - passedCount} failed${RESET}, ${passedCount} passed`;
    
    console.log(`\n${BOLD}Test Suites:${RESET} ${passedCount === tests.length ? GREEN : RED}1 ${passedCount === tests.length ? 'passed' : 'failed'}${RESET}, 1 total`);
    console.log(`${BOLD}Tests:      ${RESET} ${testsLabel}, ${tests.length} total`);
    console.log(`${BOLD}Snapshots:  ${RESET} 0 total`);
    console.log(`${BOLD}Time:       ${RESET} ${totalDuration} s`);
    console.log(`${DIM}Ran all test suites.${RESET}\n`);
    
    if (passedCount < tests.length) {
      process.exit(1);
    }
  });
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
