(function () {
  if (window.__ankiCpuGovernor) return;

  const rawConfig = window.__ankiCpuGovernorConfig || {};
  const config = {
    enabled: rawConfig.enabled !== false,
    pauseCssAnimations: rawConfig.pauseCssAnimations !== false,
    pauseRaf: rawConfig.pauseRaf !== false,
  };

  let appPaused = false;
  let docHidden = Boolean(document.hidden);
  let lastEffectivePaused = false;
  let nextSyntheticId = 1;
  const pendingCallbacks = new Map();

  const nativeRaf =
    typeof window.requestAnimationFrame === "function"
      ? window.requestAnimationFrame.bind(window)
      : (cb) => window.setTimeout(() => cb(Date.now()), 16);
  const nativeCancel =
    typeof window.cancelAnimationFrame === "function"
      ? window.cancelAnimationFrame.bind(window)
      : (id) => window.clearTimeout(id);

  function ensureStyleElement() {
    if (document.getElementById("anki-cpu-governor-style")) return;
    const target = document.head || document.documentElement;
    if (!target) return;
    const style = document.createElement("style");
    style.id = "anki-cpu-governor-style";
    style.textContent =
      "html.anki-cpu-governor-paused *, html.anki-cpu-governor-paused *::before, html.anki-cpu-governor-paused *::after { animation-play-state: paused !important; }";
    target.appendChild(style);
  }

  function isPaused() {
    return Boolean(config.enabled && (appPaused || docHidden));
  }

  function flushPendingCallbacks() {
    if (pendingCallbacks.size === 0) return;
    const entries = Array.from(pendingCallbacks.values());
    pendingCallbacks.clear();
    for (const cb of entries) {
      nativeRaf(cb);
    }
  }

  function syncDomAndDispatch() {
    const paused = isPaused();
    const root = document.documentElement;
    if (root) {
      if (paused && config.pauseCssAnimations) {
        ensureStyleElement();
        root.classList.add("anki-cpu-governor-paused");
      } else {
        root.classList.remove("anki-cpu-governor-paused");
      }
      if (paused) {
        root.dataset.cpuGovernorPaused = "1";
      } else {
        delete root.dataset.cpuGovernorPaused;
      }
    }
    if (paused !== lastEffectivePaused) {
      lastEffectivePaused = paused;
      window.dispatchEvent(
        new CustomEvent("anki-cpu-governor-change", {
          detail: { paused },
        }),
      );
    }
    if (!paused) {
      flushPendingCallbacks();
    }
  }

  window.requestAnimationFrame = function governedRequestAnimationFrame(cb) {
    if (typeof cb !== "function") {
      return nativeRaf(cb);
    }
    if (isPaused() && config.pauseRaf) {
      const id = -nextSyntheticId++;
      pendingCallbacks.set(id, cb);
      return id;
    }
    return nativeRaf(cb);
  };

  window.cancelAnimationFrame = function governedCancelAnimationFrame(id) {
    if (pendingCallbacks.delete(id)) {
      return;
    }
    nativeCancel(id);
  };

  document.addEventListener("visibilitychange", () => {
    docHidden = Boolean(document.hidden);
    syncDomAndDispatch();
  });

  window.__ankiCpuGovernor = {
    setPaused(paused) {
      appPaused = Boolean(paused);
      syncDomAndDispatch();
    },
    setEnabled(enabled) {
      config.enabled = Boolean(enabled);
      syncDomAndDispatch();
    },
    isPaused,
    getPendingCount() {
      return pendingCallbacks.size;
    },
    getConfig() {
      return Object.assign({}, config);
    },
  };

  if (docHidden && config.enabled) {
    syncDomAndDispatch();
  }
})();
