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
      rect = container.getBoundingClientRect();
    });

    container.addEventListener("mousemove", (e) => {
      if (!rect) {
        rect = container.getBoundingClientRect();
      }

      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      const rotateX = ((y - centerY) / centerY) * -10;
      const rotateY = ((x - centerX) / centerX) * 10;

      rotateXTo(rotateX);
      rotateYTo(rotateY);
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
