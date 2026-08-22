import { MARQUEE_CONFIG } from "#js/config.js";

const GRAVITY = {
  influenceRadius: 350,
  pullStrength: 55,
  pushStrength: 22,
  scaleBoost: 0.35,
  yDamping: 0.6,
  spacingCompress: 0.6, // max fraction of width to squeeze (0.6 = 60% narrower at center)
};

export function initMarquee() {
  if (
    typeof window === "undefined" ||
    !window.gsap ||
    !MARQUEE_CONFIG.enabled
  ) {
    return;
  }
  const isTouchDevice =
    "ontouchstart" in window || navigator.maxTouchPoints > 0;
  if (isTouchDevice) {
    return;
  }

  const widget = document.querySelector(".quantum-widget");
  const mWrappers = document.querySelectorAll(".marquee-container");
  const multiplier = MARQUEE_CONFIG.sizeMultiplier || 1;
  const charGroups = [];

  mWrappers.forEach((wrapper) => {
    const content = wrapper.querySelector(".marquee-content");
    if (!content) {
      return;
    }
    if (multiplier !== 1) {
      content.style.fontSize = `${multiplier * 100}%`;
    }

    if (widget) {
      splitIntoChars(content);
    }

    const clone = content.cloneNode(true);
    wrapper.appendChild(clone);

    const configDirection = MARQUEE_CONFIG.direction || 1;
    const elementDirection = wrapper.classList.contains("marquee-right")
      ? 1
      : -1;
    const direction = configDirection * elementDirection;

    if (widget) {
      const charNodes = wrapper.querySelectorAll(".mq-char");
      const spans = new Array(charNodes.length);
      for (let i = 0; i < charNodes.length; i++) {
        spans[i] = charNodes[i];
      }
      charGroups.push({ spans, direction });
    }

    window.gsap.to(wrapper.children, {
      xPercent: -100 * direction,
      ease: "none",
      duration: MARQUEE_CONFIG.animationDuration || 20,
      repeat: -1,
      modifiers: {
        xPercent: window.gsap.utils.wrap(-100, 0),
      },
    });
  });

  if (widget && charGroups.length > 0) {
    initGravitationalDistortion(widget, charGroups);
  }
}

function splitIntoChars(contentEl) {
  const originalSpan = contentEl.querySelector("span");
  if (!originalSpan) {
    return;
  }
  const text = originalSpan.textContent;
  const fragment = document.createDocumentFragment();
  for (const char of text) {
    const s = document.createElement("span");
    if (char === " ") {
      s.className = "mq-char mq-space";
      s.textContent = "\u00A0";
    } else {
      s.className = "mq-char";
      s.textContent = char;
    }
    fragment.appendChild(s);
  }
  originalSpan.replaceWith(fragment);
}

function initGravitationalDistortion(widget, charGroups) {
  const {
    influenceRadius,
    pullStrength,
    pushStrength,
    scaleBoost,
    yDamping,
    spacingCompress,
  } = GRAVITY;
  const radiusSq = influenceRadius * influenceRadius;

  // Bolt: Pre-calculate static character positions relative to their parent container
  // to avoid calling O(N) getBoundingClientRect() inside the gsap.ticker animation loop,
  // which causes severe layout thrashing and main-thread blocking.
  // Bolt: Hoist widget layout dimensions outside the ticker to prevent continuous
  // main thread layout thrashing on every 60fps frame. We cache absolute document
  // positions (adding scroll offsets) to correctly handle user scrolling.
  let wAbsoluteCx = 0;
  let wAbsoluteCy = 0;
  let widgetVisible = false;

  // Pre-allocate arrays for container bounds to prevent object allocations inside ticker
  const containerBounds = new Array(charGroups.length);
  // Cache absolute container positions to avoid getBoundingClientRect inside ticker
  const containerAbsoluteBounds = new Array(charGroups.length);

  const updateWidgetLayout = () => {
    const wRect = widget.getBoundingClientRect();
    widgetVisible = wRect.width > 0;
    if (widgetVisible) {
      wAbsoluteCx = wRect.left + window.scrollX + wRect.width / 2;
      wAbsoluteCy = wRect.top + window.scrollY + wRect.height / 2;
    }

    for (let g = 0; g < charGroups.length; g++) {
      if (charGroups[g] && charGroups[g].container) {
        const rect = charGroups[g].container.getBoundingClientRect();
        containerAbsoluteBounds[g] = {
          left: rect.left + window.scrollX,
          top: rect.top + window.scrollY,
        };
      }
    }
  };

  charGroups.forEach((group) => {
    if (group.spans.length === 0) return;

    // The wrapper that moves horizontally (e.g. .marquee-content)
    const container = group.spans[0].parentElement;
    group.container = container;

    // We cache their static offsets relative to the parent container
    const containerRect = container.getBoundingClientRect();
    group.cachedRelativePositions = new Array(group.spans.length);

    for (let i = 0; i < group.spans.length; i++) {
      const r = group.spans[i].getBoundingClientRect();
      group.cachedRelativePositions[i] = {
        xOffset: r.left + r.width / 2 - containerRect.left,
        yOffset: r.top + r.height / 2 - containerRect.top,
      };
    }
  });

  updateWidgetLayout();

  if (typeof window !== "undefined" && window.addEventListener) {
    window.addEventListener("resize", updateWidgetLayout);
    if (typeof window.ResizeObserver === "function") {
      const resizeObserver = new window.ResizeObserver(updateWidgetLayout);
      resizeObserver.observe(document.body);
    }
  }

  window.gsap.ticker.add(() => {
    if (!widgetVisible) {
      return;
    }

    // Convert cached absolute center back to viewport-relative
    // Reading scrollY doesn't cause layout thrashing
    const scrollX = window.scrollX;
    const scrollY = window.scrollY;
    const wcx = wAbsoluteCx - scrollX;
    const wcy = wAbsoluteCy - scrollY;

    // Bolt: Read container positions from absolute cache to eliminate getBoundingClientRect
    // from the high-frequency ticker loop.
    for (let g = 0; g < charGroups.length; g++) {
      const absBounds = containerAbsoluteBounds[g];
      containerBounds[g] = {
        left: absBounds.left - scrollX,
        top: absBounds.top - scrollY,
      };
    }

    // Bolt: Phase 2 (WRITE) - Batch write transforms based on dynamically computed absolute positions.
    for (let g = 0; g < charGroups.length; g++) {
      const { spans, direction, cachedRelativePositions } = charGroups[g];
      const cLeft = containerBounds[g].left;
      const cTop = containerBounds[g].top;

      for (let i = 0; i < spans.length; i += 1) {
        const absX = cLeft + cachedRelativePositions[i].xOffset;
        const absY = cTop + cachedRelativePositions[i].yOffset;

        const dx = wcx - absX;
        const dy = wcy - absY;
        const distSq = dx * dx + dy * dy;

        if (distSq >= radiusSq || distSq < 1) {
          if (spans[i].style.transform) {
            spans[i].style.transform = "";
            spans[i].style.marginLeft = "";
            spans[i].style.marginRight = "";
          }
          continue;
        }

        const dist = Math.sqrt(distSq);
        const t = 1 - dist / influenceRadius;
        const strength = t * t * t; // cubic falloff

        // Text moving left (direction < 0): chars right of center are approaching
        // Text moving right (direction > 0): chars left of center are approaching
        const isApproaching =
          (direction < 0 && dx > 0) || (direction > 0 && dx < 0);

        const force = isApproaching ? pullStrength : -pushStrength;
        const nx = dx / dist;
        const ny = dy / dist;
        const tx = nx * strength * force;
        const ty = ny * strength * Math.abs(force) * yDamping;
        const s = isApproaching
          ? 1 + strength * scaleBoost
          : 1 - strength * scaleBoost * 0.25;

        // Compress spacing — negative margins pull chars together near center
        const squeeze = strength * spacingCompress * 0.5;
        spans[i].style.marginLeft = `${(-squeeze).toFixed(2)}em`;
        spans[i].style.marginRight = `${(-squeeze).toFixed(2)}em`;

        spans[i].style.transform =
          `translate(${tx.toFixed(1)}px,${ty.toFixed(1)}px) scale(${s.toFixed(3)})`;
      }
    }
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initMarquee);
} else {
  initMarquee();
}
