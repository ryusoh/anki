export function initMagneticNav() {
  if (typeof window === "undefined" || !window.gsap) {
    return;
  }

  // Check for touch devices - usually magnetic hover feels bad on touch
  const isTouchDevice =
    "ontouchstart" in window || navigator.maxTouchPoints > 0;
  if (isTouchDevice) {
    return;
  }

  // Target nav elements and footer icons
  const magneticElements = document.querySelectorAll(
    ".container li, .nav-container li, #currencyToggleContainer .currency-toggle, #calendar-navigation-controls .cal-nav-btn",
  );

  magneticElements.forEach((el) => {
    const child = el.querySelector("a, i");
    let rect = null;

    // Pre-allocate gsap quickTo functions to avoid creating new Tweens on every mousemove
    const xTo = window.gsap.quickTo(el, "x", {
      duration: 0.3,
      ease: "power2.out",
    });
    const yTo = window.gsap.quickTo(el, "y", {
      duration: 0.3,
      ease: "power2.out",
    });

    let childXTo = null;
    let childYTo = null;
    if (child) {
      childXTo = window.gsap.quickTo(child, "x", {
        duration: 0.3,
        ease: "power2.out",
      });
      childYTo = window.gsap.quickTo(child, "y", {
        duration: 0.3,
        ease: "power2.out",
      });
    }

    el.addEventListener("mouseenter", () => {
      const r = el.getBoundingClientRect();
      // Bolt: Cache absolute layout dimensions (incorporating scroll offset)
      // on mouseenter to prevent O(N) layout thrashing inside mousemove.
      rect = {
        left: r.left + window.scrollX,
        top: r.top + window.scrollY,
        width: r.width,
        height: r.height,
      };
    });

    el.addEventListener("mousemove", (e) => {
      if (!rect) {
        const r = el.getBoundingClientRect();
        rect = {
          left: r.left + window.scrollX,
          top: r.top + window.scrollY,
          width: r.width,
          height: r.height,
        };
      }

      // Calculate absolute center of element
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;

      // Calculate distance from center to cursor using absolute page coordinates
      const distX = e.pageX - centerX;
      const distY = e.pageY - centerY;

      // Apply magnetic pull using GSAP
      // Strength of pull factor (lower = less pull)
      const strength = 0.4;

      xTo(distX * strength);
      yTo(distY * strength);

      // Pull the child element (e.g. <a> or <i>) slightly more for a parallax effect
      if (child && childXTo && childYTo) {
        childXTo(distX * (strength * 1.5));
        childYTo(distY * (strength * 1.5));
      }
    });

    el.addEventListener("mouseleave", () => {
      rect = null;
      // Elastic snap back to origin
      window.gsap.to(el, {
        x: 0,
        y: 0,
        duration: 0.7,
        ease: "elastic.out(1, 0.3)",
        overwrite: true,
      });

      if (child) {
        window.gsap.to(child, {
          x: 0,
          y: 0,
          duration: 0.7,
          ease: "elastic.out(1, 0.3)",
          overwrite: true,
        });
      }
    });
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initMagneticNav);
} else {
  initMagneticNav();
}
