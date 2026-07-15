import test, { describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import { JSDOM } from "jsdom";

describe("table_keyboard_nav.js", () => {
  let dom;

  beforeEach(() => {
    dom = new JSDOM(`
      <!DOCTYPE html>
      <html>
        <body>
          <table>
            <thead>
              <tr>
                <th class="sortable" id="th-sort">Sortable</th>
                <th class="filterable" id="th-filter">Filterable</th>
                <th id="th-normal">Normal</th>
              </tr>
            </thead>
          </table>
        </body>
      </html>
    `, { url: "http://localhost" });
    globalThis.window = dom.window;
    globalThis.document = dom.window.document;
  });

  afterEach(() => {
    delete globalThis.window;
    delete globalThis.document;
  });

  async function loadScript() {
    await import(`../js/ui/table_keyboard_nav.js?t=${Date.now()}`);
  }

  test("should set tabindex and aria-sort on headers", async () => {
    await loadScript();

    // The script attaches to DOMContentLoaded, so we call init directly or trigger event
    const event = dom.window.document.createEvent("Event");
    event.initEvent("DOMContentLoaded", true, true);
    dom.window.document.dispatchEvent(event);

    const thSort = dom.window.document.getElementById("th-sort");
    const thFilter = dom.window.document.getElementById("th-filter");
    const thNormal = dom.window.document.getElementById("th-normal");

    assert.strictEqual(thSort.getAttribute("tabindex"), "0");
    assert.strictEqual(thSort.getAttribute("aria-sort"), "none");

    assert.strictEqual(thFilter.getAttribute("tabindex"), "0");
    assert.strictEqual(thFilter.hasAttribute("aria-sort"), false); // Only .sortable gets aria-sort

    assert.strictEqual(thNormal.hasAttribute("tabindex"), false);
  });

  test("should trigger click on Enter or Space", async () => {
    await loadScript();

    const event = dom.window.document.createEvent("Event");
    event.initEvent("DOMContentLoaded", true, true);
    dom.window.document.dispatchEvent(event);

    const thSort = dom.window.document.getElementById("th-sort");
    let clickCalled = false;
    let preventDefaultCalled = false;

    thSort.addEventListener("click", () => {
      clickCalled = true;
    });

    const keydownEnter = new dom.window.KeyboardEvent("keydown", {
      key: "Enter",
      bubbles: true,
      cancelable: true
    });

    // Spy on preventDefault
    const originalPreventDefault = dom.window.Event.prototype.preventDefault;
    dom.window.Event.prototype.preventDefault = function () {
      preventDefaultCalled = true;
      originalPreventDefault.apply(this);
    };

    thSort.dispatchEvent(keydownEnter);

    assert.strictEqual(clickCalled, true);
    assert.strictEqual(preventDefaultCalled, true);

    // Reset
    clickCalled = false;
    preventDefaultCalled = false;

    const keydownSpace = new dom.window.KeyboardEvent("keydown", {
      key: " ",
      bubbles: true,
      cancelable: true
    });

    thSort.dispatchEvent(keydownSpace);

    assert.strictEqual(clickCalled, true);
    assert.strictEqual(preventDefaultCalled, true);

    // Reset and test other key
    clickCalled = false;
    preventDefaultCalled = false;

    const keydownA = new dom.window.KeyboardEvent("keydown", {
      key: "a",
      bubbles: true,
      cancelable: true
    });

    thSort.dispatchEvent(keydownA);

    assert.strictEqual(clickCalled, false);
    assert.strictEqual(preventDefaultCalled, false);
  });
});