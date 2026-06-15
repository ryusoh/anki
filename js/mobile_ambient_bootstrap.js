const MOBILE_QUERY = "(max-width: 768px)";

if (typeof window !== "undefined" && window.matchMedia(MOBILE_QUERY).matches) {
  const head = document.head || document.getElementsByTagName("head")[0];

  const loadScript = (src) =>
    new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.defer = true;
      script.src = src;
      script.onload = resolve;
      script.onerror = reject;
      head.appendChild(script);
    });

  const scripts = [
    "/js/ambient/config.js",
    "/js/ambient/loader.js",
    "/js/loader/imageFallback.js",
    "/js/ui/reduced_motion.js",
    "/js/ui/scroll_control.js",
    "/js/ui/icon_font_ready.js",
    "/js/ui/nav_current_page.js",
    "/js/ui/nav_prefetch.js",
    "/js/ui/video_warmup.js",
  ];

  Promise.all(scripts.map(loadScript))
    .then(() => import("/js/ambient/quantum_shader.js"))
    .then(() => import("/js/ui/videoFallback.js"))
    .then(({ initVideoFallback }) => {
      document.addEventListener("DOMContentLoaded", initVideoFallback);
    })
    .catch((error) => {
      // Safely ignore failures so desktop remains unaffected.

      console.warn(
        "Caught exception initializing mobile ambient/fallback:",
        error,
      );
    });
}
