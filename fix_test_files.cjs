const fs = require('fs');

let dueCode = fs.readFileSync('tests/due.test.cjs', 'utf-8');
dueCode = dueCode.replace(/console\.error\(e\);/g, 'process.exitCode = 1;\n  console.error(e);');
fs.writeFileSync('tests/due.test.cjs', dueCode);

let retentionCode = fs.readFileSync('tests/retention.test.cjs', 'utf-8');
retentionCode = retentionCode.replace(/console\.error\(e\);/g, 'process.exitCode = 1;\n  console.error(e);');
fs.writeFileSync('tests/retention.test.cjs', retentionCode);

let reviewsCode = fs.readFileSync('tests/reviews.test.cjs', 'utf-8');
reviewsCode = reviewsCode.replace(/console\.error\(e\);/g, 'process.exitCode = 1;\n  console.error(e);');
fs.writeFileSync('tests/reviews.test.cjs', reviewsCode);
