import fs from "fs";

// Replace `process.exitCode = 1` with a console.error in `.catch()` and re-throw the error
let dueCode = fs.readFileSync("tests/due.test.cjs", "utf-8");
dueCode = dueCode.replace(
  /process\.exitCode = 1;\s*console\.error\(e\);/g,
  "console.error(e);",
);
fs.writeFileSync("tests/due.test.cjs", dueCode);

let reviewsCode = fs.readFileSync("tests/reviews.test.cjs", "utf-8");
reviewsCode = reviewsCode.replace(
  /process\.exitCode = 1;\s*console\.error\(e\);/g,
  "console.error(e);",
);
fs.writeFileSync("tests/reviews.test.cjs", reviewsCode);

let retentionCode = fs.readFileSync("tests/retention.test.cjs", "utf-8");
retentionCode = retentionCode.replace(
  /process\.exitCode = 1;\s*console\.error\(e\);/g,
  "console.error(e);",
);
fs.writeFileSync("tests/retention.test.cjs", retentionCode);
