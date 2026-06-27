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

// Generate a terminal coverage report from the raw V8 coverage that the
// spawned test processes dumped into $NODE_V8_COVERAGE.
//
// We drive c8's Report class directly instead of its CLI: c8's `bin/c8.js`
// pulls in yargs, which crashes under Node 26 (`require` of yargs' extensionless
// ESM entry). The library export (`Report`) has no such dependency and works.
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
      src: [rootDir],
      all: false,
      excludeNodeModules: true,
      exclude: [
        '**/node_modules/**',
        '**/tests/**',
        '**/*.test.*',
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
  } catch (e) {
    console.log(`\n\x1b[2mCoverage report skipped: ${e.message}\x1b[0m`);
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
  // turn it into a human-readable report here.
  if (process.env.NODE_V8_COVERAGE) {
    await generateCoverageReport();
  }

  console.log(`\n\x1b[1mTest Suites:\x1b[0m ${failed > 0 ? '\x1b[31m' + failed + ' failed\x1b[0m, ' : ''}\x1b[32m${passed} passed\x1b[0m, ${results.length} total`);
  console.log(`\x1b[1mTests:      \x1b[0m ${failed > 0 ? '\x1b[31m' + failed + ' failed\x1b[0m, ' : ''}\x1b[32m${passed} passed\x1b[0m, ${results.length} total`);
  console.log(`\x1b[1mSnapshots:  \x1b[0m 0 total`);
  console.log(`\x1b[1mTime:       \x1b[0m ${totalTime} s`);
  console.log(`\x1b[2mRan all test suites.\x1b[0m\n`);

  if (failed > 0) {
    process.exit(1);
  }
}

runAllTests().catch(err => {
  console.error('Test runner failed:', err);
  process.exit(1);
});
