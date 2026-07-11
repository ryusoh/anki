/**
 * Polyfills for jsdom behavioral gaps under the pinned version (^27.3.0).
 *
 * jsdom is pinned to 27.x because 27.4+ pulls in html-encoding-sniffer@6
 * which depends on @exodus/bytes (ESM-only). Jest's CJS require() cannot
 * load ESM-only packages on Node < 24.9, so upgrading jsdom breaks the
 * review_heatmap jest suites.
 *
 * jsdom 27's Blob does not expose .arrayBuffer(). Tests that exercise
 * production code calling blob.arrayBuffer() (e.g. stats_page_customizer's
 * injected.js fetch-patching) need this polyfill.
 *
 * The polyfill is guarded by a feature check so it becomes a no-op if
 * jsdom is eventually upgraded.
 */

/**
 * Polyfill Blob.prototype.arrayBuffer on a jsdom window if missing.
 * Call this right after `new JSDOM(...)` before running any scripts.
 *
 * @param {Window} window - The jsdom window object (dom.window)
 */
function polyfillBlobArrayBuffer(window) {
  if (typeof window.Blob.prototype.arrayBuffer === "function") return;
  window.Blob.prototype.arrayBuffer = function () {
    return new Promise((resolve, reject) => {
      const r = new window.FileReader();
      r.onload = () => resolve(r.result);
      r.onerror = () => reject(r.error);
      r.readAsArrayBuffer(this);
    });
  };
}

module.exports = { polyfillBlobArrayBuffer };
