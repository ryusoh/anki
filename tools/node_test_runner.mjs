import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';
import os from 'os';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.join(__dirname, '..');

// Find all test files matching *.test.js, *.test.cjs, *.test.mjs
const findTestFiles = (dir, fileList = []) => {
  const files = fs.readdirSync(dir);

  for (const file of files) {
    // Skip node_modules and dot folders
    if (file === 'node_modules' || file.startsWith('.')) continue;

    const filePath = path.join(dir, file);
    if (fs.statSync(filePath).isDirectory()) {
      findTestFiles(filePath, fileList);
    } else if (file.endsWith('.test.js') || file.endsWith('.test.cjs') || file.endsWith('.test.mjs')) {
      fileList.push(filePath);
    }
  }

  return fileList;
};

async function runTest(file) {
  return new Promise((resolve) => {
    const startTime = Date.now();
    const isEsm = file.endsWith('.mjs') || file.endsWith('.js');
    
    // Command based on file type
    const cmd = isEsm ? 'node' : 'node';
    const args = isEsm ? ['--experimental-vm-modules', '--no-warnings', file] : [file];

    const proc = spawn(cmd, args, {
      cwd: rootDir,
      env: { ...process.env, NODE_ENV: 'test' }
    });

    let output = '';
    let errorOutput = '';

    proc.stdout.on('data', (data) => {
      output += data.toString();
    });

    proc.stderr.on('data', (data) => {
      errorOutput += data.toString();
    });

    proc.on('close', (code) => {
      const duration = ((Date.now() - startTime) / 1000).toFixed(2);
      resolve({
        file: path.relative(rootDir, file),
        success: code === 0,
        code,
        output,
        errorOutput,
        duration
      });
    });
  });
}

// Whole-suite coverage floor (docs/lint-and-quality.md): thresholds live in
// package.json's "c8" key (the conventional c8 config location). The floor
// stops silent whole-suite erosion that per-file work can miss; it is set
// slightly below the measured totals and ratcheted upward, never down.
// Returns true when the floor is met (or no floor is configured).
async function checkCoverageFloor(report) {
  const pkg = JSON.parse(fs.readFileSync(path.join(rootDir, 'package.json'), 'utf8'));
  const thresholds = pkg.c8 || {};
  const keys = ['lines', 'branches', 'functions', 'statements'].filter(
    (k) => typeof thresholds[k] === 'number'
  );
  if (keys.length === 0) return true;

  // After report.run() the merged map is memoized, so this is cheap.
  const map = await report.getCoverageMapFromAllCoverageFiles();
  const summary = map.getCoverageSummary();
  let ok = true;
  for (const key of keys) {
    const pct = summary[key].pct;
    if (pct < thresholds[key]) {
      console.error(
        `\x1b[31mERROR: Coverage for ${key} (${pct}%) does not meet global threshold (${thresholds[key]}%)\x1b[0m`
      );
      ok = false;
    }
  }
  return ok;
}

// Generate a terminal coverage report from the raw V8 coverage that the
// spawned test processes dumped into $NODE_V8_COVERAGE.
//
// We drive c8's Report class directly instead of its CLI: c8's `bin/c8.js`
// pulls in yargs, which crashes under Node 26 (`require` of yargs' extensionless
// ESM entry). The library export (`Report`) has no such dependency and works.
// Returns false when the whole-suite coverage floor (package.json "c8") fails.
async function generateCoverageReport() {
  // When COVERAGE_SUMMARY_DIR is set (the `coverage-rank` target does this), keep
  // the report directory and additionally emit a machine-readable json-summary so
  // tools/coverage_rank.py can rank files. Otherwise use a throwaway temp dir.
  const summaryDir = process.env.COVERAGE_SUMMARY_DIR;
  const reportsDirectory = summaryDir
    ? (fs.mkdirSync(summaryDir, { recursive: true }), summaryDir)
    : fs.mkdtempSync(path.join(os.tmpdir(), 'c8-report-'));
  try {
    const { Report } = await import('c8');
    const report = new Report({
      tempDirectory: process.env.NODE_V8_COVERAGE,
      reportsDirectory,
      // 'text' = per-file table with uncovered line numbers (≈ pytest's
      // term-missing); 'text-summary' = the totals block.
      reporter: summaryDir
        ? ['text', 'text-summary', 'json-summary']
        : ['text', 'text-summary'],
      // `all: true` puts every first-party source file in the denominator, so
      // files with zero tests show up at 0% instead of being silently absent.
      // The src dirs mirror eslint.config.cjs's scope: all JS we maintain,
      // minus vendored trees and minified bundles (excluded below).
      src: [
        path.join(rootDir, 'js'),
        path.join(rootDir, 'animated_glass_background', 'web'),
        path.join(rootDir, 'enhance_main_window'),
      ],
      all: true,
      excludeNodeModules: true,
      exclude: [
        '**/node_modules/**',
        '**/tests/**',
        '**/*.test.*',
        '**/*.min.js',
        'coverage/**',
        'js/vendor/**',
        'assets/**',
      ],
      omitRelative: true,
      resolve: '',
      wrapperLength: 0,
    });
    console.log('\n\x1b[1mCoverage Report:\x1b[0m');
    await report.run();
    return await checkCoverageFloor(report);
  } catch (e) {
    console.log(`\n\x1b[2mCoverage report skipped: ${e.message}\x1b[0m`);
    return true;
  } finally {
    if (!summaryDir) {
      fs.rmSync(reportsDirectory, { recursive: true, force: true });
    }
  }
}

async function runAllTests() {
  console.log('\n\x1b[1m🚀 Running Node.js Test Suite...\x1b[0m\n');

  const testFiles = findTestFiles(path.join(rootDir, 'tests'));
  
  if (testFiles.length === 0) {
    console.log('No tests found.');
    return;
  }

  const results = [];
  let passed = 0;
  let failed = 0;

  // Run sequentially for predictable output
  for (const file of testFiles) {
    const result = await runTest(file);
    results.push(result);
    
    if (result.success) {
      process.stdout.write('\x1b[32m✓\x1b[0m ');
      passed++;
    } else {
      process.stdout.write('\x1b[31m✕\x1b[0m ');
      failed++;
    }
    
    // Wrap dot output
    if ((passed + failed) % 40 === 0) {
      console.log('');
    }
  }

  console.log('\n\n\x1b[1mTest Summary:\x1b[0m');
  
  // Print failures first
  const failedTests = results.filter(r => !r.success);
  for (const r of failedTests) {
    const fileParts = r.file.split('/');
    const fileName = fileParts.pop();
    const dirStr = fileParts.length ? fileParts.join('/') + '/' : '';

    console.log(`  \x1b[41m\x1b[37m FAIL \x1b[0m \x1b[2m${dirStr}\x1b[0m\x1b[1m${fileName}\x1b[0m \x1b[2m(${r.duration}s)\x1b[0m`);
    
    // Print failure output (limiting length)
    console.log('\n\x1b[31m\x1b[1m--- Failure Output ---\x1b[0m');
    
    // Clean up stack traces slightly for readability
    let cleanErr = r.errorOutput || r.output || 'Unknown error';
    
    // Truncate if insanely long
    if (cleanErr.length > 5000) {
      cleanErr = cleanErr.substring(0, 5000) + '\n... [output truncated] ...';
    }

    console.log(cleanErr);
    console.log('\x1b[31m\x1b[1m----------------------\x1b[0m\n');
  }

  // Print passes
  for (const r of results.filter(r => r.success)) {
    const fileParts = r.file.split('/');
    const fileName = fileParts.pop();
    const dirStr = fileParts.length ? fileParts.join('/') + '/' : '';

    // Dim the directory, highlight the filename
    console.log(`  \x1b[42m\x1b[30m PASS \x1b[0m \x1b[2m${dirStr}\x1b[0m\x1b[1m${fileName}\x1b[0m \x1b[33m(${r.duration}s)\x1b[0m`);
  }

  const totalTime = results.reduce((acc, r) => acc + parseFloat(r.duration), 0).toFixed(2);

  // When invoked with NODE_V8_COVERAGE set (the `check-node` Makefile target
  // does this), the spawned test processes dump raw V8 coverage into that dir;
  // turn it into a human-readable report here and enforce the whole-suite
  // coverage floor from package.json's "c8" key.
  let coverageOk = true;
  if (process.env.NODE_V8_COVERAGE) {
    coverageOk = await generateCoverageReport();
  }

  console.log(`\n\x1b[1mTest Suites:\x1b[0m ${failed > 0 ? '\x1b[31m' + failed + ' failed\x1b[0m, ' : ''}\x1b[32m${passed} passed\x1b[0m, ${results.length} total`);
  console.log(`\x1b[1mTests:      \x1b[0m ${failed > 0 ? '\x1b[31m' + failed + ' failed\x1b[0m, ' : ''}\x1b[32m${passed} passed\x1b[0m, ${results.length} total`);
  console.log(`\x1b[1mSnapshots:  \x1b[0m 0 total`);
  console.log(`\x1b[1mTime:       \x1b[0m ${totalTime} s`);
  console.log(`\x1b[2mRan all test suites.\x1b[0m\n`);

  if (failed > 0 || !coverageOk) {
    process.exit(1);
  }
}

runAllTests().catch(err => {
  console.error('Test runner failed:', err);
  process.exit(1);
});
