// Flat ESLint config. We own and lint the addon source in this repo; only
// genuinely vendored libraries and minified bundles are excluded.
module.exports = [
    {
        ignores: [
            '.claude/**',
            '.venv/**',
            'node_modules/**',
            'coverage/**',
            'graph_output/**',
            'data/**',
            'assets/vendor/**',
            'js/vendor/**',
            '**/*.min.js',
            // Vendored libraries bundled inside owned addons
            'review_heatmap/libaddon/**',
            '**/_vendor/**',
            // Legacy/vendored/injected bundles and script files
            'review_heatmap/web/anki-review-heatmap.js',
            'stats_page_customizer/injected.js',
            'awesome_tts/awesometts/service/sapi5js.js',
        ],
    },
    {
        files: ['**/*.js'],
        languageOptions: {
            ecmaVersion: 'latest',
            sourceType: 'module',
            globals: {
                window: 'readonly',
                document: 'readonly',
                navigator: 'readonly',
                console: 'readonly',
                setTimeout: 'readonly',
                clearTimeout: 'readonly',
                setInterval: 'readonly',
                clearInterval: 'readonly',
                fetch: 'readonly',
                performance: 'readonly',
                requestAnimationFrame: 'readonly',
                cancelAnimationFrame: 'readonly',
                Image: 'readonly',
                CustomEvent: 'readonly',
                Event: 'readonly',
                KeyboardEvent: 'readonly',
                MouseEvent: 'readonly',
                Element: 'readonly',
                HTMLCanvasElement: 'readonly',
                getComputedStyle: 'readonly',
                MutationObserver: 'readonly',
                IntersectionObserver: 'readonly',
                ResizeObserver: 'readonly',
                requestIdleCallback: 'readonly',
                cancelIdleCallback: 'readonly',
                Blob: 'readonly',
                Response: 'readonly',
                Request: 'readonly',
                FormData: 'readonly',
                FileReader: 'readonly',
                AbortController: 'readonly',
                URL: 'readonly',
                URLSearchParams: 'readonly',
                localStorage: 'readonly',
                sessionStorage: 'readonly',
                location: 'readonly',
                // Anki webview bridge + injected globals
                pycmd: 'readonly',
                bridgeCommand: 'readonly',
                MathJax: 'readonly',
                // Common vendored libs referenced from first-party code
                d3: 'readonly',
                Chart: 'readonly',
                gsap: 'readonly',
                $: 'readonly',
                define: 'readonly',
                module: 'readonly',
                XMLSerializer: 'readonly',
            },
        },
        rules: {
            // Cyclomatic-complexity ratchet (docs/lint-and-quality.md), max 20;
            // eslint-suppressions.json baselines the existing violations (ESLint
            // bulk suppressions only apply to errors), so only NEW or worsened
            // violations fail. After fixing one, run
            // `npx eslint --prune-suppressions` to shrink the baseline.
            complexity: ['error', { max: 20 }],
            'no-undef': 'error',
            'no-unused-vars': [
                'warn',
                {
                    args: 'after-used',
                    ignoreRestSiblings: true,
                    argsIgnorePattern: '^_',
                    varsIgnorePattern: '^_',
                },
            ],
            'no-unreachable': 'error',
            'no-constant-binary-expression': 'error',
            'no-var': 'warn',
            'prefer-const': ['warn', { destructuring: 'all' }],
            'no-useless-return': 'warn',
            eqeqeq: ['warn', 'always', { null: 'ignore' }],
        },
    },
    {
        // Node-based test runners and tooling scripts
        files: ['**/tests/**/*.js', '**/*.test.js', '**/*.test.mjs', 'tools/**/*.mjs'],
        languageOptions: {
            globals: {
                require: 'readonly',
                module: 'readonly',
                process: 'readonly',
                __dirname: 'readonly',
                global: 'readonly',
                Buffer: 'readonly',
                jest: 'readonly',
                describe: 'readonly',
                it: 'readonly',
                test: 'readonly',
                expect: 'readonly',
                beforeEach: 'readonly',
                afterEach: 'readonly',
            },
            sourceType: 'module',
        },
        rules: {
            'no-unused-vars': 'off',
        },
    },
];
