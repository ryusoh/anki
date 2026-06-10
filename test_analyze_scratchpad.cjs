const assert = require('assert');

async function run() {
    global.window = {
        Chart: class { constructor(ctx, config) { this.config = config; this.data = config.data; } destroy() {} update() {} },
        document: { querySelector: () => null }
    };
    global.document = {
        querySelector: () => null,
        getElementById: () => ({ getContext: () => ({}), classList: { remove: () => {} }, querySelectorAll: () => [], style: {}, appendChild: () => {}, textContent: '' }),
        createElement: () => ({ setAttribute: () => {}, appendChild: () => {}, style: {} }),
        createTextNode: () => ({})
    };
    global.gsap = { timeline: () => ({ to: function(){ return this; }, call: function() { return this; }}) };

    const { renderReviewsChart } = await import('./js/commands/reviews.js');
    const fakeData = [{ date: "2023-01-01", count: 10, time: 3600, mature: 1, young: 1, learn: 1, relearn: 1 }];
    fakeData.decks = ["Deck1"];
    fakeData.byDeck = { "Deck1": fakeData };
    fakeData.preSliceSum = { count: 0, time: 0 };
    fakeData.preSliceSumsByDeck = { "Deck1": { count: 0, time: 0 } };

    // byDeck = true, showTime = true, cumulative = false => hits 390, 391
    renderReviewsChart(fakeData, true, true, false);

    // byDeck = true, showTime = false, cumulative = true => hits 392, 393
    renderReviewsChart(fakeData, false, true, true);

    // not byDeck => length <= 100 => hits 604, 605
    renderReviewsChart(fakeData, false, false, false);
}
run().catch(console.error);
