const assert = require('assert');

// Setup minimal mocks
global.gsap = {
    timeline: () => ({
        to: function() { return this; },
        call: function() { return this; }
    })
};
const windowMock = {
  Chart: class {},
  gsap: global.gsap,
  customStatsData: {
    futureDue: [],
    futureDueByDeck: {},
    reviewStats: []
  },
  innerWidth: 1024
};
global.window = windowMock;
global.self = windowMock;
global.document = {
  getElementById: (id) => ({
    id,
    classList: { add: () => {}, remove: () => {}, contains: () => false },
    innerHTML: '',
    style: {},
    appendChild: () => {},
    scrollTop: 0,
    scrollHeight: 0,
    getBoundingClientRect: () => ({ top: 0, bottom: 0, height: 100 }),
    clientHeight: 100,
    dataset: {}
  }),
  querySelector: () => null,
  querySelectorAll: () => []
};

async function runCoverage() {
    const { handleCommand } = await import('../js/commands/handler.js');

    const appendLine = (text, variant) => {};

    // Hit invalid ranges across all plot permutations
    handleCommand('reviews time cumulative xyz', appendLine);
    handleCommand('reviews deck cumulative xyz', appendLine);
    handleCommand('reviews cumulative xyz', appendLine);
    handleCommand('reviews time deck xyz', appendLine);
    handleCommand('reviews deck time xyz', appendLine);
    handleCommand('reviews time xyz', appendLine);
    handleCommand('reviews deck xyz', appendLine);
    handleCommand('reviews xyz', appendLine);

    // show nonexistent
    handleCommand('show nonexistent', appendLine);

    // Hit zoom catch
    handleCommand('zoom', appendLine);

    console.log("✅ handler extra coverage handled");
}

runCoverage().catch(e => {
    console.error(e);
    process.exit(1);
});
