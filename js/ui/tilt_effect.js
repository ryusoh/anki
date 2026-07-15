import { TILT_EFFECT } from "#js/config.js";

export function initTiltEffect() {
  if (!TILT_EFFECT.enabled || typeof window === "undefined" || !window.gsap) {
    return;
  }
  const isTouchOnly =
    ("ontouchstart" in window || navigator.maxTouchPoints > 0) &&
    !window.matchMedia("(pointer: fine)").matches;
  if (isTouchOnly) {
    return;
  }
  const tiltContainers = document.querySelectorAll(
    "nav.container, .quantum-widget, .marquee-container",
  );
  tiltContainers.forEach((container) => {
    let rect = null;

    window.gsap.set(container, {
      transformPerspective: 1000,
      transformStyle: "preserve-3d",
    });

    // Pre-allocate gsap quickTo functions to avoid creating new Tweens on every mousemove
    const rotateXTo = window.gsap.quickTo(container, "rotateX", {
      duration: 0.5,
      ease: "power2.out",
    });
    const rotateYTo = window.gsap.quickTo(container, "rotateY", {
      duration: 0.5,
      ease: "power2.out",
    });

    container.addEventListener("mouseenter", () => {
      const r = container.getBoundingClientRect();
      // Bolt: Cache absolute layout dimensions (incorporating scroll offset)
      // on mouseenter to prevent O(N) layout thrashing inside mousemove.
      rect = {
        left: r.left + window.scrollX,
        top: r.top + window.scrollY,
        width: r.width,
        height: r.height,
      };
    });

    let ticking = false;
    container.addEventListener("mousemove", (e) => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          if (!rect) {
            const r = container.getBoundingClientRect();
            rect = {
              left: r.left + window.scrollX,
              top: r.top + window.scrollY,
              width: r.width,
              height: r.height,
            };
          }

          const x = e.pageX - rect.left;
          const y = e.pageY - rect.top;
          const centerX = rect.width / 2;
          const centerY = rect.height / 2;
          const rotateX = ((y - centerY) / centerY) * -10;
          const rotateY = ((x - centerX) / centerX) * 10;

          rotateXTo(rotateX);
          rotateYTo(rotateY);
          ticking = false;
        });
        ticking = true;
      }
    });
    container.addEventListener("mouseleave", () => {
      rect = null;
      window.gsap.to(container, {
        rotateX: 0,
        rotateY: 0,
        duration: 1,
        ease: "elastic.out(1, 0.3)",
        overwrite: true,
      });
    });
  });
}
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initTiltEffect);
} else {
  initTiltEffect();
}
