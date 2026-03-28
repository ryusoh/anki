const assert = require('assert');

let capturedConfig = null;
global.window = {
    Chart: class {
        constructor(ctx, config) {
            this.config = config || {};
            this.data = this.config.data || { datasets: [] };
            capturedConfig = config;

            if (ctx === 'THROW') {
                throw new Error('Chart render error');
            }
        }
        destroy() {}
        update() {}
        setDatasetVisibility() {}
        isDatasetVisible() { return true; }
    },
    reviewStatsData: {
        reviews: [
            { id: 1690000000000, type: 1, ease: 2 },
            { id: 1690086400000, type: 1, ease: 3 }
        ]
    }
};

global.document = {
    getElementById: (id) => {
        if (id === 'runningAmountCanvas') return { getContext: () => ({}) };
        if (id === 'runningAmountSection') return { classList: { remove: () => {} } };
        if (id === 'chartLegend') return { style: {}, innerHTML: '', querySelectorAll: () => [] };
        if (id === 'runningAmountEmpty') return { style: {}, textContent: '' };
        return null;
    },
    querySelector: () => null
};

async function runTests() {
    console.log('🧪 Running Retention Tests');

    // Suppress console.error in tests to avoid test runner thinking it failed if there is no error code
    console.error = () => {};

    const { destroyRetentionChart, renderRetentionChart, showRetention } = await import('../js/commands/retention.js');

    const resEmpty = renderRetentionChart([]);
    assert.strictEqual(resEmpty.success, false);

    const validData = [
        { date: '2023-01-01', retention: 0.8 },
        { date: '2023-01-02', retention: 0.9 }
    ];
    let resValid = renderRetentionChart(validData);
    assert.strictEqual(resValid.success, true);

    const originalGetContext = global.document.getElementById;
    global.document.getElementById = (id) => {
        if (id === 'runningAmountCanvas') return { getContext: () => 'THROW' };
        return originalGetContext(id);
    };
    const resFail = renderRetentionChart(validData);
    assert.strictEqual(resFail.success, false);
    global.document.getElementById = originalGetContext;

    resValid = renderRetentionChart(validData);
    assert.doesNotThrow(() => destroyRetentionChart());

    const denseData = Array.from({length: 201}, (_, i) => ({ date: `2023-01-${i}`, retention: 0.8 }));
    assert.strictEqual(renderRetentionChart(denseData).success, true);

    const oldStats = global.window.reviewStatsData;
    global.window.reviewStatsData = null;
    assert.strictEqual(showRetention(), "Review stats not loaded yet. Please wait a moment and try again.");
    global.window.reviewStatsData = oldStats;

    destroyRetentionChart();

    console.log('✅ Retention tests passed\n');
}

runTests().catch(err => {
    // If there is an actual failure in test execution
    console.log('❌ Retention tests failed:', err);
    process.exitCode = 1;
});
