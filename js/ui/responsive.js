import { UI_BREAKPOINTS, CALENDAR_SELECTORS } from "#js/config.js";
import { debounce } from "../utils/debounce.js";

export function checkAndToggleVerticalScroll() {
  const isMobile = window.innerWidth <= UI_BREAKPOINTS.MOBILE;
  const htmlElement = document.documentElement;
  const bodyElement = document.body;

  if (!isMobile) {
    // Ensure scrolling is enabled on desktop
    htmlElement.style.overflowY = ""; // Reset to default
    bodyElement.style.overflowY = ""; // Reset to default
  }
}

// Bolt Performance Optimization:
// Cache DOM references so we don't query the document repeatedly on every scroll/resize frame.
// We initialize them lazily to ensure the elements are actually present in the DOM.
let mobileToggleContainer, mobileChartContainer;

export function alignToggleWithChartMobile() {
  const isMobile = window.innerWidth <= UI_BREAKPOINTS.MOBILE;

  if (!mobileToggleContainer) {
    mobileToggleContainer = document.getElementById("currencyToggleContainer");
  }
  if (!mobileChartContainer) {
    mobileChartContainer = document.getElementById("fundPieChartContainer");
  }

  if (!mobileToggleContainer || !mobileChartContainer) {
    return;
  }

  if (isMobile) {
    // Ensure toggle is fixed for JS positioning to work as intended relative to viewport
    mobileToggleContainer.style.position = "fixed";
    mobileToggleContainer.style.left = "0px"; // Keep it stuck to the left

    const chartRect = mobileChartContainer.getBoundingClientRect();
    const chartCenterY = chartRect.top + chartRect.height / 2;

    const toggleHeight = mobileToggleContainer.offsetHeight;
    const toggleTop = chartCenterY - toggleHeight / 2;

    mobileToggleContainer.style.top = `${toggleTop}px`;
  } else {
    // Reset styles if not mobile, so desktop CSS takes over
    mobileToggleContainer.style.position = ""; // Reverts to CSS defined position (e.g. fixed, top: 15px, left: 15px)
    mobileToggleContainer.style.top = "";
    mobileToggleContainer.style.left = ""; // Allow desktop CSS to control left
  }
}

export function setupResizeListener() {
  const handleResize = debounce(() => {
    checkAndToggleVerticalScroll();
    alignToggleWithChartMobile();
  }, 100);

  window.addEventListener("resize", handleResize);
}

export function initCalendarResponsiveHandlers() {
  // Bolt Performance Optimization:
  // Cache DOM references so we don't query the document repeatedly on every scroll/resize frame.
  // We initialize them lazily to ensure the elements are actually present in the DOM.
  let toggleContainer, heatmapRoot, calendarContainer, navControls;

  const alignToggle = () => {
    const isMobile = window.innerWidth <= UI_BREAKPOINTS.MOBILE;

    if (!toggleContainer) {
      toggleContainer = document.querySelector(
        CALENDAR_SELECTORS.currencyToggle,
      );
    }
    if (!heatmapRoot) {
      heatmapRoot = document.querySelector(CALENDAR_SELECTORS.heatmap);
    }
    if (!calendarContainer) {
      calendarContainer = document.querySelector(CALENDAR_SELECTORS.container);
    }
    if (!navControls) {
      navControls = document.querySelector(CALENDAR_SELECTORS.navControls);
    }

    if (!toggleContainer || !heatmapRoot) {
      return;
    }

    const normalizeRect = (rect) => {
      if (!rect || typeof rect.top !== "number") {
        return null;
      }
      const top = rect.top;
      const bottom =
        typeof rect.bottom === "number"
          ? rect.bottom
          : top + (rect.height || 0);
      const height = bottom - top;
      if (!(height > 0)) {
        return null;
      }
      return { top, bottom, height };
    };

    const rectFromElement = (element) => {
      if (!element || typeof element.getBoundingClientRect !== "function") {
        return null;
      }
      return normalizeRect(element.getBoundingClientRect());
    };

    const mergeRects = (rects) => {
      if (!rects.length) {
        return null;
      }
      if (rects.length === 1) {
        return rects[0];
      }
      const top = Math.min(...rects.map((rect) => rect.top));
      const bottom = Math.max(...rects.map((rect) => rect.bottom));
      return { top, bottom, height: bottom - top };
    };

    const resolveHeatmapRect = () => {
      const domainNodes = heatmapRoot.querySelectorAll("[data-ch-domain]");
      const domainRects = Array.from(domainNodes)
        .map((node) => rectFromElement(node))
        .filter(Boolean);

      if (domainRects.length) {
        return mergeRects(domainRects);
      }

      const svgRect = rectFromElement(heatmapRoot.querySelector("svg"));
      if (svgRect) {
        return svgRect;
      }

      const firstChildRect = rectFromElement(heatmapRoot.firstElementChild);
      if (firstChildRect) {
        return firstChildRect;
      }

      if (calendarContainer) {
        const containerRect = rectFromElement(calendarContainer);
        if (containerRect) {
          return containerRect;
        }
      }

      return rectFromElement(heatmapRoot);
    };

    if (isMobile) {
      toggleContainer.style.removeProperty("left");
      toggleContainer.style.removeProperty("right");
      const heatmapRect = resolveHeatmapRect();
      if (!heatmapRect) {
        return;
      }
      let targetRect = heatmapRect;
      const navRect = rectFromElement(navControls);
      if (navRect) {
        targetRect = mergeRects([heatmapRect, navRect]);
      }
      if (!targetRect) {
        return;
      }
      const targetCenterY = targetRect.top + targetRect.height / 2;
      toggleContainer.style.setProperty(
        "top",
        `${targetCenterY}px`,
        "important",
      );
    } else {
      toggleContainer.style.removeProperty("position");
      toggleContainer.style.removeProperty("top");
      toggleContainer.style.removeProperty("left");
      toggleContainer.style.removeProperty("right");
      toggleContainer.style.removeProperty("transform");
    }
  };

  alignToggle();

  const scheduleAlignResize = debounce(() => {
    window.requestAnimationFrame(() => {
      alignToggle();
    });
  }, 100);

  let ticking = false;
  const scheduleAlignScroll = () => {
    if (!ticking) {
      window.requestAnimationFrame(() => {
        alignToggle();
        ticking = false;
      });
      ticking = true;
    }
  };

  window.addEventListener("resize", scheduleAlignResize);
  window.addEventListener("scroll", scheduleAlignScroll, { passive: true });
  window.addEventListener("calendar-zoom-end", scheduleAlignResize);
  if (typeof window !== "undefined" && window.ResizeObserver) {
    const observer = new window.ResizeObserver(scheduleAlignResize);

    // Fallback to query in case alignToggle hasn't cached these yet,
    // though usually alignToggle() is called above initializing them.
    const obsToggle =
      toggleContainer ||
      document.querySelector(CALENDAR_SELECTORS.currencyToggle);
    const obsHeatmap =
      heatmapRoot || document.querySelector(CALENDAR_SELECTORS.heatmap);
    const obsCalendar =
      calendarContainer || document.querySelector(CALENDAR_SELECTORS.container);
    const obsNav =
      navControls || document.querySelector(CALENDAR_SELECTORS.navControls);

    if (obsToggle) {
      observer.observe(obsToggle);
    }
    if (obsHeatmap) {
      observer.observe(obsHeatmap);
    }
    if (obsCalendar) {
      observer.observe(obsCalendar);
    }
    if (obsNav) {
      observer.observe(obsNav);
    }
  }

  const todayButton = document.querySelector(CALENDAR_SELECTORS.todayButton);
  const pageWrapper = document.querySelector(CALENDAR_SELECTORS.pageWrapper);
  if (todayButton && pageWrapper) {
    todayButton.addEventListener("dblclick", () => {
      if (window.innerWidth <= UI_BREAKPOINTS.MOBILE) {
        return;
      }
      const isZoomed = pageWrapper.classList.toggle("zoomed");
      const body = document.body;
      if (body && body.classList) {
        body.classList.toggle("calendar-zoomed", isZoomed);
      }
      pageWrapper.addEventListener(
        "transitionend",
        () => {
          window.dispatchEvent(new CustomEvent("calendar-zoom-end"));
        },
        { once: true },
      );
    });
  }
}
