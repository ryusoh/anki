(function () {
  "use strict";

  const PREFETCH_DELAY = 1800;
  const IDLE_TIMEOUT = 2000;
  const MEDIA_MANIFEST = {
    home: [
      { url: "assets/mobile_bg.jpg", type: "image" },
      { url: "assets/mobile_bg.mp4", type: "video" },
    ],
    terminal: [],
  };
  const CSS_BACKGROUND_SOURCES = {
    shared: [],
    home: ["css/main_index.css"],
    terminal: ["css/terminal/base.css"],
  };
  const BACKGROUND_URL_REGEX =
    /background(?:-image)?\s*:[^;{}]*url\(([^)]+)\)/gi;
  const ROUTE_SLUGS = {
    home: "",
    terminal: "terminal/",
  };

  function normalizePath(pathname) {
    if (!pathname) {
      return "/";
    }
    let normalized = pathname.replace(/index\.html$/i, "");
    if (!normalized.endsWith("/")) {
      normalized += "/";
    }
    return normalized;
  }

  function getConnectionProfile() {
    const navConnection =
      navigator.connection ||
      navigator.mozConnection ||
      navigator.webkitConnection;
    const effectiveType = navConnection && navConnection.effectiveType;
    return {
      saveData: Boolean(navConnection && navConnection.saveData),
      slow: effectiveType === "slow-2g" || effectiveType === "2g",
    };
  }

  function findAppBase() {
    const manifestLink = document.querySelector('link[rel="manifest"]');
    if (manifestLink) {
      try {
        const href = manifestLink.getAttribute("href");
        if (!href || href.length > 2000 || window.location.href.length > 2000)
          return;
        const manifestUrl = new window.URL(href, window.location.href);
        const manifestPath = manifestUrl.pathname;
        const marker = "/assets/manifest.webmanifest";
        const markerIndex = manifestPath.lastIndexOf(marker);
        if (markerIndex !== -1) {
          return normalizePath(manifestPath.slice(0, markerIndex + 1));
        }
      } catch (error) {
        console.warn(
          "Caught exception parsing manifest URL, falling back to window location:",
          error,
        );
      }
    }

    return normalizePath(window.location.pathname.replace(/[^/]*$/, ""));
  }

  function buildRoutePaths(appBase) {
    const paths = {};
    Object.keys(ROUTE_SLUGS).forEach((key) => {
      const slug = ROUTE_SLUGS[key];
      if (!slug) {
        paths[key] = normalizePath(appBase);
      } else {
        const base = appBase.endsWith("/") ? appBase : `${appBase}/`;
        paths[key] = normalizePath(`${base}${slug}`);
      }
    });
    return paths;
  }

  function determineCurrentRoute(routePaths) {
    const current = normalizePath(window.location.pathname);
    return (
      Object.keys(routePaths).find((key) => routePaths[key] === current) ||
      (current === "/" ? "home" : undefined)
    );
  }

  function resolveAssetUrl(appBase, asset) {
    if (!asset || !asset.url) {
      return undefined;
    }

    if (/^https?:\/\//i.test(asset.url)) {
      return asset.url;
    }

    const sanitized = asset.url.replace(/^\//, "");
    const base = appBase.endsWith("/") ? appBase : `${appBase}/`;
    const originBase = `${window.location.origin}${base}`;
    if (sanitized.length > 2000 || originBase.length > 2000) return undefined;
    return new window.URL(sanitized, originBase).href;
  }

  function queueFetchTask(url, queue, seen) {
    if (seen.has(url)) {
      return;
    }
    seen.add(url);
    queue.push(() => {
      let fetchUrl;
      try {
        if (!url || url.length > 2000) return undefined;
        fetchUrl = new window.URL(url);
      } catch (error) {
        console.warn("Caught exception:", error);
        return undefined;
      }

      const isCrossOrigin = fetchUrl.origin !== window.location.origin;

      const options = {
        credentials: isCrossOrigin ? "omit" : "same-origin",
        cache: "force-cache",
        redirect: "follow",
      };

      if (isCrossOrigin) {
        options.mode = "no-cors";
      }

      return fetch(fetchUrl.href, options).catch(() => undefined);
    });
  }

  function drainQueue(queue) {
    if (!queue.length) {
      return;
    }

    const runNext = () => {
      if (!queue.length) {
        return;
      }
      const task = queue.shift();
      Promise.resolve()
        .then(task)
        .catch(() => undefined)
        .finally(() => {
          if (queue.length) {
            if ("requestIdleCallback" in window) {
              window.requestIdleCallback(runNext, { timeout: IDLE_TIMEOUT });
            } else {
              window.setTimeout(runNext, IDLE_TIMEOUT);
            }
          }
        });
    };

    if ("requestIdleCallback" in window) {
      window.requestIdleCallback(runNext, { timeout: IDLE_TIMEOUT });
    } else {
      window.setTimeout(runNext, PREFETCH_DELAY);
    }
  }

  function shouldSkipAsset(asset, connection) {
    if (!asset) {
      return true;
    }
    if (asset.type === "video" && connection.slow) {
      return true;
    }
    if (asset.skipOnSlow && connection.slow) {
      return true;
    }
    return false;
  }

  function queueCssBackgrounds(
    routeKey,
    appBase,
    connection,
    queue,
    seen,
    tasks,
  ) {
    const files = CSS_BACKGROUND_SOURCES[routeKey];
    if (!files || !files.length) {
      return;
    }

    files.forEach((path) => {
      const cssUrl = resolveAssetUrl(appBase, { url: path });
      if (!cssUrl) {
        return;
      }

      const discoveryTask = fetchCssBackgrounds(cssUrl).then((urls) => {
        urls.forEach((assetUrl) => {
          const asset = { url: assetUrl, type: "image", skipOnSlow: true };
          if (shouldSkipAsset(asset, connection)) {
            return;
          }
          queueFetchTask(assetUrl, queue, seen);
        });
      });

      tasks.push(
        discoveryTask.catch(() => {
          return undefined;
        }),
      );
    });
  }

  function fetchCssBackgrounds(cssUrl) {
    return fetch(cssUrl, {
      credentials: "same-origin",
      cache: "force-cache",
      redirect: "follow",
    })
      .then((res) => {
        if (!res || !res.ok) {
          return [];
        }
        return res.text().then((text) => extractBackgroundUrls(text, cssUrl));
      })
      .catch(() => []);
  }

  function extractBackgroundUrls(cssText, cssUrl) {
    if (!cssText) {
      return [];
    }

    const urls = new Set();
    BACKGROUND_URL_REGEX.lastIndex = 0;

    let match;
    while ((match = BACKGROUND_URL_REGEX.exec(cssText))) {
      if (!match || match.length < 2) {
        continue;
      }

      let rawUrl = match[1].trim();
      if (!rawUrl) {
        continue;
      }

      rawUrl = rawUrl.replace(/^['"]|['"]$/g, "");

      if (!rawUrl || rawUrl.startsWith("data:")) {
        continue;
      }

      try {
        if (!rawUrl || rawUrl.length > 2000 || !cssUrl || cssUrl.length > 2000)
          return;
        const resolved = new window.URL(rawUrl, cssUrl).href;
        urls.add(resolved);
      } catch (error) {
        console.warn("Caught exception:", error);
        // Ignore invalid URLs
      }
    }

    return Array.from(urls);
  }

  function schedulePrefetch() {
    if (document.visibilityState === "hidden") {
      return;
    }

    const connection = getConnectionProfile();
    if (connection.saveData) {
      return;
    }

    const appBase = findAppBase();
    const routePaths = buildRoutePaths(appBase);
    const currentRoute = determineCurrentRoute(routePaths);

    if (!currentRoute) {
      return;
    }

    const queue = [];
    const seen = new Set();
    const cssDiscoveryTasks = [];
    const normalizedCurrentPath =
      routePaths[currentRoute] || normalizePath(window.location.pathname);

    const navLinks = document.querySelectorAll(
      ".container a[href], .nav-container a[href]",
    );
    navLinks.forEach((link) => {
      const href = link.getAttribute("href");
      if (!href || href.startsWith("#")) {
        return;
      }
      let resolved;
      try {
        if (href.length > 2000 || window.location.href.length > 2000) return;
        resolved = new window.URL(href, window.location.href);
      } catch (error) {
        console.warn("Caught exception:", error);
        return;
      }
      if (resolved.origin !== window.location.origin) {
        return;
      }
      if (normalizePath(resolved.pathname) === normalizedCurrentPath) {
        return;
      }
      queueFetchTask(resolved.href, queue, seen);
    });

    queueCssBackgrounds(
      "shared",
      appBase,
      connection,
      queue,
      seen,
      cssDiscoveryTasks,
    );

    const routeKeys = Object.keys(routePaths);
    for (let i = 0, len = routeKeys.length; i < len; i++) {
      const key = routeKeys[i];
      if (key === currentRoute) continue;
      const assets = MEDIA_MANIFEST[key];
      if (!assets || !assets.length) {
        continue;
      }
      for (let j = 0, alen = assets.length; j < alen; j++) {
        const asset = assets[j];
        if (!asset || !asset.url) continue;
        if (shouldSkipAsset(asset, connection)) continue;
        const assetUrl = resolveAssetUrl(appBase, asset);
        if (assetUrl) {
          queueFetchTask(assetUrl, queue, seen);
        }
      }
      queueCssBackgrounds(
        key,
        appBase,
        connection,
        queue,
        seen,
        cssDiscoveryTasks,
      );
    }

    const finalizePrefetch = () => {
      if (!queue.length) {
        return;
      }
      window.setTimeout(() => {
        drainQueue(queue);
      }, PREFETCH_DELAY);
    };

    if (cssDiscoveryTasks.length) {
      const settleAll = Promise.allSettled
        ? Promise.allSettled(cssDiscoveryTasks)
        : Promise.all(cssDiscoveryTasks);
      settleAll.finally(finalizePrefetch);
    } else {
      finalizePrefetch();
    }
  }

  if (document.readyState === "complete") {
    schedulePrefetch();
  } else {
    window.addEventListener("load", schedulePrefetch, { once: true });
  }
})();
