/* istanbul ignore file */
/* Simple CDN fallback loader (no modules). Exposes window.CDNLoader */
(function () {
  if (window.CDNLoader) {
    return;
  }
  /**
   * @param {string[]} origins
   */
  function preconnect(origins) {
    try {
      for (let i = 0; i < origins.length; i++) {
        const l = document.createElement("link");
        l.rel = "preconnect";
        l.href = origins[i];
        l.crossOrigin = "anonymous";
        document.head.appendChild(l);
      }
    } catch (error) {
      console.warn("Caught exception:", error);
    }
  }
  /**
   * @param {string[]} urls
   * @param {{ defer?: boolean, async?: boolean }} [attrs]
   * @returns {Promise<void>}
   */
  function loadScriptSequential(urls, attrs) {
    return new Promise(function (resolve, reject) {
      (function next(i) {
        if (i >= urls.length) {
          return reject(new Error("all failed: " + urls.join(", ")));
        }
        const s = document.createElement("script");
        s.src = urls[i];
        s.crossOrigin = "anonymous";
        if (attrs && attrs.defer) {
          s.defer = true;
        }
        if (attrs && attrs.async) {
          s.async = true;
        }
        s.onload = function () {
          resolve(undefined);
        };
        s.onerror = function () {
          next(i + 1);
        };
        document.head.appendChild(s);
      })(0);
    });
  }
  /**
   * @param {string[]} urls
   * @returns {Promise<void>}
   */
  function loadCssWithFallback(urls) {
    return new Promise(function (resolve) {
      (function next(i) {
        if (i >= urls.length) {
          // Final fallback: fetch last and inline
          const last = urls[urls.length - 1];
          fetch(last, { mode: "cors" })
            .then(function (r) {
              return r.ok ? r.text() : Promise.reject();
            })
            .then(function (css) {
              const style = document.createElement("style");
              style.textContent = css;
              document.head.appendChild(style);
              resolve(undefined);
            })
            .catch(function (error) {
              console.warn("Caught exception:", error);
              resolve(undefined);
            });
          return;
        }
        const link = document.createElement("link");
        link.rel = "stylesheet";
        link.href = urls[i];
        link.crossOrigin = "anonymous";
        link.onload = function () {
          resolve(undefined);
        };
        link.onerror = function () {
          next(i + 1);
        };
        document.head.appendChild(link);
      })(0);
    });
  }
  window.CDNLoader = {
    preconnect: preconnect,
    loadScriptSequential: loadScriptSequential,
    loadCssWithFallback: loadCssWithFallback,
  };
})();
