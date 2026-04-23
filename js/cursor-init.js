// Custom cursor and UI enhancements
import { initCursor } from "./vendor/cursor.js?v=20240223";

function boot() {
  const isGraphPage = window.location.pathname.includes("/graph/");
  const { cursor } = initCursor({
    cursor: {
      hoverTargets:
        "a, button, .container li, .nav-container li, #timeline-slider",
      followEase: isGraphPage ? 0.8 : 0.4,
      fadeEase: 0.1,
      hoverScale: 3,
    },
  });
  window.cursorInstances = { cursor };
}

document.addEventListener("DOMContentLoaded", () => {
  if (window.gsap) {
    boot();
    return;
  }

  // GSAP may be deferred by Cloudflare Rocket Loader — poll briefly
  let attempts = 0;
  const id = setInterval(() => {
    attempts += 1;
    if (window.gsap) {
      clearInterval(id);
      boot();
    } else if (attempts >= 40) {
      // Give up after ~2 s
      clearInterval(id);
    }
  }, 50);
});
