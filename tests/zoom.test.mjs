import test from 'node:test';
import assert from 'node:assert';

test('Zoom module logic', async () => {
    // We can test getZoomElements and toggleZoom by mocking the DOM globally
    global.document = {
        getElementById: (id) => {
            if (id === 'terminal') return {
                classList: {
                    add: () => {},
                    remove: () => {}
                },
                getBoundingClientRect: () => ({ top: 10, bottom: 200, height: 190 })
            };
            if (id === 'runningAmountSection') return {
                classList: {
                    add: () => {},
                    remove: () => {},
                    contains: () => false
                },
                getBoundingClientRect: () => ({ bottom: 500 })
            };
            if (id === 'terminalOutput') return {
                dataset: {},
                getBoundingClientRect: () => ({ height: 150 })
            };
            return null;
        }
    };

    // We also need to mock GSAP for toggleZoom to work
    global.gsap = {
        timeline: (opts) => {
            // Immediately resolve the completion handler to bypass animation delays in tests
            if (opts && opts.onComplete) {
                setTimeout(opts.onComplete, 0);
            }
            return {
                to: () => {}
            };
        },
        set: () => {}
    };

    const zoom = await import('../js/commands/zoom.js');

    assert.strictEqual(zoom.getZoomState(), false);

    const result1 = await zoom.toggleZoom();
    assert.strictEqual(result1.zoomed, true);
    assert.strictEqual(zoom.getZoomState(), true);

    const result2 = await zoom.toggleZoom();
    assert.strictEqual(result2.zoomed, false);
    assert.strictEqual(zoom.getZoomState(), false);
});

test('Zoom graceful degradation when terminal elements are missing', async () => {
    // Override mock to simulate missing elements
    const originalGetElementById = global.document.getElementById;
    global.document.getElementById = (id) => null;

    const zoom = await import('../js/commands/zoom.js');

    // Ensure we start from a clean state (it should just fail gracefully)
    const result = await zoom.toggleZoom();
    assert.strictEqual(result.zoomed, false);
    assert.ok(result.message.includes('not found'));

    // Restore mock
    global.document.getElementById = originalGetElementById;
});

test('Zoom calculates fallback output height when chart is missing', async () => {
    const originalGetElementById = global.document.getElementById;

    global.document.getElementById = (id) => {
        if (id === 'terminal') return {
            classList: { add: () => {}, remove: () => {} },
            getBoundingClientRect: () => ({ top: 10, bottom: 200, height: 190 })
        };
        if (id === 'runningAmountSection') return null; // simulate missing chart
        if (id === 'terminalOutput') return {
            dataset: {},
            getBoundingClientRect: () => ({ height: 150 })
        };
        return null;
    };

    const zoom = await import('../js/commands/zoom.js');

    // Ensure we start from a clean zoomed out state
    if (zoom.getZoomState()) {
        await zoom.toggleZoom();
    }

    // Toggle will trigger calculateZoomedOutputHeight with chart = null
    const result = await zoom.toggleZoom();
    assert.strictEqual(result.zoomed, true);
    assert.strictEqual(zoom.getZoomState(), true);

    // Clean up state and mocks
    await zoom.toggleZoom();
    global.document.getElementById = originalGetElementById;
});
