/* Service worker for Anki.
 *
 * Strategy summary:
 *   - Live data (/data/anki/*.json, /graph/*.json): network first so stats stay
 *     fresh, with cache fallback for offline.
 *   - Images, fonts, and media: cache first (immutable-ish, speed priority).
 *   - HTML, CSS, JS: stale-while-revalidate — serve the cached copy instantly
 *     for app-like navigation between pages, refresh the cache in the
 *     background so the next visit picks up deploys.
 *
 * Bump CACHE_NAME whenever the core asset list changes so the install event
 * precaches the new shell and the activate event prunes the old cache.
 */
const CACHE_NAME = "anki-cache-2026-07-27a";
const CORE_ASSETS = [
  "/",
  "/index.html",
  "/terminal/",
  "/graph/",
  "/css/base.css",
  "/css/layout.css",
  "/css/main_index.css",
  "/css/container.css",
  "/css/table.css",
  "/css/toggle.css",
  "/css/perf.css",
  "/css/cursor.css",
  "/css/marquee.css",
  "/css/graph.css",
  "/css/terminal/base.css",
  "/css/terminal/terminal.css",
  "/css/terminal/table.css",
  "/css/terminal/chart.css",
  "/css/terminal/responsive.css",
  "/js/loader/cdnFallback.js",
  "/js/ui/service_worker_register.js",
  "/js/ui/scroll_control.js",
  "/js/ui/nav_current_page.js",
  "/js/ui/nav_prefetch.js",
  "/js/ui/icon_font_ready.js",
  "/js/ui/reduced_motion.js",
  "/js/ui/magnetic_nav.js",
  "/js/ui/tilt_effect.js",
  "/js/ui/tableGlassEffect.js",
  "/js/ui/marquee.js",
  "/js/ui/videoFallback.js",
  "/js/ui/video_warmup.js",
  "/js/cursor-init.js",
  "/js/config.js",
  "/js/vendor/gsap.min.js",
  "/js/vendor/cursor.js",
  "/assets/vendor/css/font-awesome-4.7.0.min.css",
  "/assets/vendor/fonts/fontawesome-webfont.woff2",
  "/assets/icons/icon-180.png",
  "/assets/manifest.webmanifest",
  "/assets/mobile_bg.jpg",
  "/assets/banners/banner.png",
  "/assets/backgrounds/graph_background.jpg",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(CORE_ASSETS))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys.map((key) => {
            if (key !== CACHE_NAME) {
              return caches.delete(key);
            }
          }),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

const isValidResponse = (res, req) => {
  return (
    res &&
    res.ok &&
    res.status === 200 &&
    res.type === "basic" &&
    !req.headers.has("range") &&
    !res.headers.get("Content-Range")
  );
};

const putInCache = (req, res) => {
  const resClone = res.clone();
  return caches.open(CACHE_NAME).then((cache) => cache.put(req, resClone));
};

const fetchAndCache = (req) => {
  return fetch(req).then((res) => {
    if (isValidResponse(res, req)) {
      putInCache(req, res);
    }
    return res;
  });
};

const cacheFirst = (req) => {
  return caches.match(req, { ignoreVary: true }).then((cached) => {
    if (cached) {
      return cached;
    }
    return fetchAndCache(req);
  });
};

const networkFirst = (req) => {
  return fetchAndCache(req).catch(() =>
    caches.match(req, { ignoreVary: true }),
  );
};

const staleWhileRevalidate = (event, req) => {
  return caches.match(req, { ignoreVary: true }).then((cached) => {
    const refresh = fetchAndCache(req);
    if (cached) {
      event.waitUntil(refresh.catch(() => undefined));
      return cached;
    }
    return refresh.catch(() => caches.match(req, { ignoreVary: true }));
  });
};

self.addEventListener("fetch", (event) => {
  const req = event.request;

  if (req.method !== "GET") {
    return;
  }

  const url = new URL(req.url);

  if (url.origin !== self.location.origin) {
    return;
  }

  if (req.headers.has("range")) {
    return;
  }

  const pathname = url.pathname;

  if (pathname.startsWith("/data/") || pathname.startsWith("/graph/")) {
    event.respondWith(networkFirst(req));
    return;
  }

  const isImmutable =
    req.destination === "image" ||
    req.destination === "font" ||
    pathname.endsWith(".png") ||
    pathname.endsWith(".jpg") ||
    pathname.endsWith(".jpeg") ||
    pathname.endsWith(".woff2") ||
    pathname.endsWith(".woff") ||
    pathname.endsWith(".ttf") ||
    pathname.endsWith(".mp4") ||
    pathname.endsWith(".webm");

  if (isImmutable) {
    event.respondWith(cacheFirst(req));
  } else {
    event.respondWith(staleWhileRevalidate(event, req));
  }
});
