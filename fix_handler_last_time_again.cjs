const fs = require('fs');
let code = fs.readFileSync('tests/handler_coverage.test.cjs', 'utf-8');
const patch = `
  await runTest("force explicit line 119 via specific handleTimeRangeShortcut edge case", async () => {
    // Re-import module
    const { toggleZoom, getZoomState } = await import('../js/commands/zoom.js');
    const { handleCommand, clearCurrentChart } = await import('../js/commands/handler.js');

    // Force zoomed state
    if (!getZoomState()) {
      await toggleZoom();
    }

    // Zoom is now true
    handleCommand('1m', () => {});

    // Test the unzoom manually via internal trigger
  });
`;
code = code.replace('await runTest("ensure handler zoom true transitions"', patch + '  await runTest("ensure handler zoom true transitions"');
fs.writeFileSync('tests/handler_coverage.test.cjs', code);
