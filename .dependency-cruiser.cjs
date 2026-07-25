/** @type {import('dependency-cruiser').IConfiguration} */
module.exports = {
    forbidden: [
        {
            name: 'no-circular',
            comment:
                'Circular deps make modules untestable in isolation (docs/lint-and-quality.md — dependency-structure gate)',
            severity: 'error',
            from: {},
            to: { circular: true },
        },
        // Deliberately NOT ported from the fund reference: the cross-page rule
        // (this repo has no js/pages/ concept) and the not-to-vendor rule (this
        // repo's designated loader js/cursor-init.js imports js/vendor/cursor.js
        // directly — measured 1 violation on day one, so the rule would gate the
        // repo's own accepted pattern). See docs/lint-and-quality.md.
    ],
    options: {
        // Alias resolution for #js/ #ui/ #utils/ lives in
        // .dependency-cruiser.webpack.cjs (see that file for why it's a webpack
        // stub and not options.tsConfig — short version: the tsConfig route
        // prints a spurious "missing-typescript-transpiler" warning).
        webpackConfig: { fileName: '.dependency-cruiser.webpack.cjs' },
        doNotFollow: { path: 'node_modules' },
        // js/vendor is third-party (AGENTS.md non-negotiable #5: never touch);
        // cruising it would gate code we don't own.
        exclude: { path: '^js/vendor' },
    },
};
