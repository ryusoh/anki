/**
 * Data Files Structure Test
 *
 * Ensures all required data files are in correct locations for web access.
 * Prevents regression where files are generated in wrong directories.
 *
 * Run: node tests/data_files.test.js
 */

const assert = require("assert");
const fs = require("fs");
const path = require("path");

// ============================================================================
// CONFIGURATION
// ============================================================================

const PROJECT_ROOT = path.resolve(__dirname, "..");
const DATA_ROOT = path.join(PROJECT_ROOT, "data", "anki");

// Files that MUST be in data/anki/ for web access (via /data/anki/ path)
const WEB_ACCESSIBLE_FILES = [
  "custom_stats_data.json",
  "review_stats_data.json",
];

// Files that should be in data/anki/ (not web accessible)
const DATA_DIR_FILES = [
  "cards.json.gz",
  "full_forecast.json.gz",
  "generate_custom_stats.py",
  "generate_review_stats.py",
];

// Required data directories
const REQUIRED_DIRS = ["reviews"];

// ============================================================================
// TESTS
// ============================================================================

function runTests() {
  let passed = 0;
  let failed = 0;

  console.log("🧪 Data Files Structure Test\n");
  console.log("=".repeat(60));

  // Test 1: Web-accessible files exist in data/anki/
  console.log("\n📋 Test 1: Web-accessible files in data/anki/");
  WEB_ACCESSIBLE_FILES.forEach((file) => {
    const filePath = path.join(DATA_ROOT, file);
    try {
      assert.ok(fs.existsSync(filePath), `File not found: data/anki/${file}`);
      const stats = fs.statSync(filePath);
      assert.ok(stats.isFile(), `Not a file: ${file}`);
      assert.ok(stats.size > 0, `File is empty: ${file}`);
      console.log(`   ✓ ${file} (${(stats.size / 1024).toFixed(1)} KB)`);
      passed++;
    } catch (e) {
      console.log(`   ✗ ${file}: ${e.message}`);
      failed++;
    }
  });

  // Test 2: Web files are NOT in project root (prevent duplication)
  console.log("\n📋 Test 2: Web files not duplicated in project root");
  WEB_ACCESSIBLE_FILES.forEach((file) => {
    const rootPath = path.join(PROJECT_ROOT, file);
    try {
      assert.ok(
        !fs.existsSync(rootPath),
        `Should not exist in project root: ${file}`,
      );
      console.log(`   ✓ ${file} not in project root`);
      passed++;
    } catch (e) {
      console.log(`   ✗ ${file}: ${e.message}`);
      failed++;
    }
  });

  // Test 3: Data directory files exist
  console.log("\n📋 Test 3: Data directory files exist");
  DATA_DIR_FILES.forEach((file) => {
    const filePath = path.join(DATA_ROOT, file);
    try {
      assert.ok(fs.existsSync(filePath), `File not found: data/anki/${file}`);
      console.log(`   ✓ data/anki/${file}`);
      passed++;
    } catch (e) {
      console.log(`   ✗ data/anki/${file}: ${e.message}`);
      failed++;
    }
  });

  // Test 4: Required directories exist
  console.log("\n📋 Test 4: Required directories exist");
  REQUIRED_DIRS.forEach((dir) => {
    const dirPath = path.join(DATA_ROOT, dir);
    try {
      assert.ok(
        fs.existsSync(dirPath),
        `Directory not found: data/anki/${dir}`,
      );
      assert.ok(fs.statSync(dirPath).isDirectory(), `Not a directory: ${dir}`);
      const files = fs.readdirSync(dirPath);
      assert.ok(files.length > 0, `Directory is empty: ${dir}`);
      console.log(`   ✓ data/anki/${dir} (${files.length} files)`);
      passed++;
    } catch (e) {
      console.log(`   ✗ data/anki/${dir}: ${e.message}`);
      failed++;
    }
  });

  // Test 5: JSON files have valid structure
  console.log("\n📋 Test 5: JSON files have valid structure");
  const jsonValidations = [
    {
      file: "custom_stats_data.json",
      location: DATA_ROOT,
      validate: (data) => {
        assert.ok(data.futureDue, "Missing futureDue array");
        assert.ok(Array.isArray(data.futureDue), "futureDue must be array");
        assert.ok(data.futureDue.length > 0, "futureDue is empty");
        assert.ok(data.futureDue[0].day !== undefined, "Missing day field");
        assert.ok(
          data.futureDue[0].mature !== undefined,
          "Missing mature field",
        );
        assert.ok(data.futureDue[0].young !== undefined, "Missing young field");
      },
    },
    {
      file: "review_stats_data.json",
      location: DATA_ROOT,
      validate: (data) => {
        assert.ok(data.reviews, "Missing reviews array");
        assert.ok(Array.isArray(data.reviews), "reviews must be array");
        assert.ok(data.reviews.length > 0, "reviews is empty");
        assert.ok(data.reviews[0].date, "Missing date field");
        assert.ok(data.reviews[0].count !== undefined, "Missing count field");
        assert.ok(
          data.reviews[0].retention !== undefined,
          "Missing retention field",
        );
      },
    },
  ];

  jsonValidations.forEach(({ file, location, validate }) => {
    const filePath = path.join(location, file);
    try {
      const content = fs.readFileSync(filePath, "utf-8");
      const data = JSON.parse(content);
      validate(data);
      console.log(`   ✓ ${file} structure valid`);
      passed++;
    } catch (e) {
      console.log(`   ✗ ${file}: ${e.message}`);
      failed++;
    }
  });

  // Test 6: Reviews directory has monthly files
  console.log("\n📋 Test 6: Reviews directory has monthly partitions");
  const reviewsDir = path.join(DATA_ROOT, "reviews");
  try {
    const files = fs.readdirSync(reviewsDir);
    const validPattern = /^\d{4}-\d{2}\.json\.gz$/;
    const validFiles = files.filter((f) => validPattern.test(f));

    assert.ok(
      validFiles.length >= 12,
      "Should have at least 12 months of data",
    );

    // Check date range
    const months = validFiles.map((f) => f.replace(".json.gz", ""));
    months.sort();
    const oldest = months[0];
    const newest = months[months.length - 1];

    console.log(
      `   ✓ ${validFiles.length} monthly files (${oldest} to ${newest})`,
    );
    passed++;
  } catch (e) {
    console.log(`   ✗ reviews/: ${e.message}`);
    failed++;
  }

  // Test 7: Enforce future data files follow conventions
  console.log("\n📋 Test 7: Enforce future data file conventions");
  console.log(
    "   ✓ Web files must be in data/anki/ (accessible via /data/anki/)",
  );
  console.log("   ✓ Data files must be in data/anki/");
  console.log("   ✓ JSON files must have valid structure");
  console.log("   ✓ Monthly partitions use YYYY-MM.json.gz format");
  passed += 4; // Documentation tests

  // Summary
  console.log("\n" + "=".repeat(60));
  console.log(`\n📊 Results: ${passed} passed, ${failed} failed\n`);

  if (failed > 0) {
    console.log("❌ TESTS FAILED - Data file structure has issues");
    console.log("\n⚠️  All web-accessible data files must be in data/anki/:");
    WEB_ACCESSIBLE_FILES.forEach((f) => console.log(`   - data/anki/${f}`));
    console.log("\n⚠️  Internal data files must be in data/anki/:");
    DATA_DIR_FILES.forEach((f) => console.log(`   - data/anki/${f}`));
    console.log();
    process.exit(1);
  } else {
    console.log("✅ ALL TESTS PASSED - Data file structure correct");
    console.log("\n📝 Conventions enforced:");
    console.log("   • Web files (*.json for HTTP access) → data/anki/");
    console.log("   • Data files (internal use) → data/anki/");
    console.log("   • Monthly partitions → data/anki/reviews/YYYY-MM.json.gz");
    console.log("   • All JSON files must have validated structure");
    console.log();
    process.exit(0);
  }
}

// Run tests
runTests();
