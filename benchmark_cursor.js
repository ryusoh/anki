import { JSDOM } from 'jsdom';

const dom = new JSDOM(`<!DOCTYPE html><p>Hello world</p>`, {
  url: "https://example.org/",
  referrer: "https://example.com/",
  contentType: "text/html",
  includeNodeLocations: true,
  storageQuota: 10000000
});

const window = dom.window;
const sessionStorage = window.sessionStorage;

const iterations = 10000;
let totalTime = 0;

for(let j = 0; j < 5; j++) {
    const start = performance.now();
    for (let i = 0; i < iterations; i++) {
        sessionStorage.setItem('cursorPosition', JSON.stringify({ x: 100 + i, y: 200 + i }));
    }
    const end = performance.now();
    totalTime += (end - start);
}

console.log(`Average time for 10000 sessionStorage writes: ${totalTime / 5}ms`);
