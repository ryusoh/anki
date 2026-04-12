import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

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
    const args = isEsm ? ['--experimental-vm-modules', file] : [file];

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

  // Try to generate code coverage with c8 if available
  let coverageSuccess = false;
  try {
    // Only run coverage report generation if this runner was wrapped in c8
    if (process.env.NODE_V8_COVERAGE) {
      console.log('\n\x1b[1mCoverage Report (Real):\x1b[0m');
      // The c8 wrap will automatically generate the report on exit
      coverageSuccess = true;
    }
  } catch (e) {
    // Coverage generation failed, but tests might have passed
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
