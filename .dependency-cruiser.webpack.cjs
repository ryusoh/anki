// Webpack-config stub for dependency-cruiser (.dependency-cruiser.cjs) only —
// NOT a real build config; this repo has no bundler. It exists because
// dependency-cruiser resolves import-map aliases (#js/, #ui/, …) through
// either options.tsConfig or a webpack resolve.alias, and the tsConfig route
// makes it look for a typescript <7 compiler (repo has v7) and print a
// spurious "missing-typescript-transpiler" warning on every run.
//
// Note: #js/ and #ui/ also resolve natively via package.json "imports"
// (enhanced-resolve reads it); the stub keeps resolution explicit and covers
// "#utils/", which exists only in the import maps. Keep the aliases below in
// sync with package.json "imports" and the import maps in index.html,
// terminal/index.html, and graph/index.html. `roots` resolves web-root-
// absolute imports ("/js/…" in js/mobile_ambient_bootstrap.js) — without it
// they surface as 2 fake modules (41 modules cruised instead of 39).
const path = require('path');

const r = (p) => path.resolve(__dirname, p);

module.exports = {
    resolve: {
        alias: {
            '#js': r('js'),
            '#ui': r('js/ui'),
            '#utils': r('js/utils'),
        },
        roots: [r('.')],
    },
};
