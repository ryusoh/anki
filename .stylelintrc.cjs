// Stylelint config for first-party CSS only. Mirrors the rule set used in the
// fund repo. Third-party addon CSS and vendored bundles are excluded via
// .stylelintignore.
const rules = {
    'color-no-invalid-hex': true,
    'font-family-no-duplicate-names': true,
    'function-linear-gradient-no-nonstandard-direction': true,
    'string-no-newline': true,
    'unit-no-unknown': true,
    'property-no-unknown': true,
    'declaration-block-no-duplicate-properties': [
        true,
        { ignore: ['consecutive-duplicates-with-different-values'] },
    ],
    'block-no-empty': true,
    'color-hex-length': 'short',
};

module.exports = { rules };
