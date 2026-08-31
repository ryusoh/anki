export const DATA_PATHS = {
  customStats: "/data/anki/custom_stats_data.json",
  reviewStats: "/data/anki/review_stats_data.json",
  graphData: "/graph/graph_data.json",
};

export const CALENDAR_SELECTORS = {
  container: "#calendar-container",
  heatmap: "#cal-heatmap",
  prevButton: "#cal-prev",
  nextButton: "#cal-next",
  todayButton: "#cal-today",
  currencyToggle: "#currencyToggleContainer",
  pageWrapper: ".page-center-wrapper",
  navControls: "#calendar-navigation-controls",
};

// Dynamic calendar range calculation based on viewport and zoom state
export const getCalendarRange = () => {
  const isZoomed =
    document.querySelector(".page-center-wrapper.zoomed") !== null;
  const viewportWidth = window.innerWidth;

  // Calculate available space for calendar
  // Account for padding, margins, and UI elements
  /* c8 ignore next */
  const availableWidth = isZoomed ? viewportWidth * 0.85 : viewportWidth * 0.9;

  // Estimate space needed for each month (approximate)
  // Each month needs ~280px width minimum for good readability
  const monthWidth = 280;
  const maxMonths = Math.floor(availableWidth / monthWidth);

  // Responsive breakpoints with zoom awareness
  /* c8 ignore next 3 */
  if (viewportWidth <= 480 || (isZoomed && viewportWidth <= 768)) {
    return 1; // Mobile or zoomed on small screens
  }
  /* c8 ignore next 8 */
  if (viewportWidth <= 768 || (isZoomed && viewportWidth <= 1024)) {
    return Math.min(2, maxMonths); // Tablet or zoomed on medium screens
  }
  if (viewportWidth <= 1200 || (isZoomed && viewportWidth <= 1600)) {
    return Math.min(3, maxMonths); // Desktop or zoomed on large screens
  }
  return Math.min(3, maxMonths); // Large desktop - max 3 months
};

export const CALENDAR_CONFIG = {
  vertical: false,
  itemSelector: CALENDAR_SELECTORS.heatmap,
  range: getCalendarRange(),
  scale: {
    color: {
      type: "diverging",
      range: [
        "rgba(244, 67, 54, 0.95)",
        "rgba(120, 120, 125, 0.5)",
        "rgba(76, 175, 80, 0.95)",
      ],
      domain: [-0.01, 0.01],
    },
  },
  domain: {
    type: "month",
    padding: [10, 10, 10, 10],
    label: { text: "MMMM YYYY", textAlign: "center", position: "top" },
  },
  subDomain: {
    type: "day",
    radius: 3,
    width: 45,
    height: 45,
    gutter: 6,
    label: () => "",
    color: () => "white",
  },
};

export const CALENDAR_BACKGROUND_EFFECT = {
  enabled: true,
  // Duration of the visible sweep effect in seconds
  // Controls how fast the light moves across the screen
  sweepDuration: 3,
  // Time to wait after a sweep finishes before the next one starts
  sweepPauseTime: 2,
  // Colors for the chromatic aberration effect
  // Format: 'R, G, B' (without 'rgba' or parenthesis)
  colors: {
    color1: "50, 100, 255", // Optical Blue (Leading Edge)
    color2: "255, 50, 80", // Optical Red (Trailing Edge)
  },
};

export const TERMINAL_BACKGROUND_EFFECT = {
  enabled: true,
  sweepDuration: 2,
  sweepPauseTime: 0,
  colors: {
    color1: "60, 120, 255",
    color2: "255, 80, 160",
  },
};

export const CALENDAR_MONTH_LABEL_BACKGROUND = {
  paddingX: 10,
  paddingY: 5,
  radius: 14,
  fill: "rgba(80, 80, 80, 0.8)",
  stroke: "rgba(255, 255, 255, 0.1)",
  strokeWidth: 0.8,
  opacity: 1,
  blurStdDeviation: 8,
  alphaSlope: 0.65,
  transitionDuration: 220,
  maxWidth: undefined,
  enabled: false,
};

export const CALENDAR_MONTH_LABEL_HIGHLIGHT = {
  intervalMs: 40,
  waveSize: 4,
  baseColor: "rgba(255, 255, 255, 0.95)",
  neutralDimColor: "rgba(150, 150, 150, 0.65)",
  waveAlpha: 0.85,
  pnlLightenFactor: 0.55,
  pnlLightAlpha: 0.85,
};

export const PIE_CHART_GLASS_EFFECT = {
  enabled: true,
  opacity: 0.75, // Default fallback; overridden via responsiveOpacity at runtime
  responsiveOpacity: {
    desktop: 0.4,
    mobile: 0.4,
  },
  // All border settings in one place
  borders: {
    // Slice separation borders (between pie slices)
    sliceWidth: 1, // Thinner, more delicate borders
    sliceColor: "rgba(0, 0, 0, 0.1)", // Subtle white borders like iOS
    // Outer/inner arc borders (for customArcBordersPlugin)
    arcWidth: 1.5, // Thinner arc borders
    arcColor: "rgba(0, 0, 0, 0.15)", // Very subtle white outline
    // Border style
    style: "solid", // Clean, crisp lines
  },
  // Enhanced liquid glass properties
  liquidGlass: {
    // Add subtle gradient overlay for depth
    gradientOverlay: true,
    gradientStart: "rgba(255, 255, 255, 0.3)", // Top highlight
    gradientEnd: "rgba(255, 255, 255, 0.02)", // Bottom subtle
    // Saturation boost for more vibrant liquid look
    saturationBoost: 1.4, // 40% more saturated colors
    // Optical distortion for glass refraction effect
    distortion: {
      enabled: true,
      strength: 2, // Barrel distortion coefficient (positive = barrel, negative = pincushion)
      type: "barrel", // 'barrel' for outward bulge effect
      smoothEdges: true, // Smooth distortion falloff at edges
      quality: "medium", // 'low', 'medium', 'high' - affects performance vs quality
      // Configurable overlay colors for distortion effect - QUANTUM COMPUTATION FIELD
      overlayColors: {
        inner: "rgba(0, 229, 255, 0.45)", // Quantum coherence core - computational precision
        middle: "rgba(38, 198, 218, 0.32)", // Superposition field - qubit entanglement
        outer: "rgba(77, 182, 172, 0.22)", // Quantum interference edge - algorithmic resonance
      },
      // Animation and movement settings
      animation: {
        speed: 0.002, // Overall animation speed (0.001 = very slow, 0.01 = fast)
        movement: {
          hotspotRange: 1.2, // How far the light hotspot moves (0.5 = moderate, 1.2 = extreme)
          colorBlockRange: 0.8, // How far the entire color block moves (0.2 = subtle, 0.8 = dramatic)
          xFrequency: 1.3, // X-axis movement frequency multiplier
          yFrequency: 1.3, // Y-axis movement frequency multiplier
        },
        colors: {
          shiftIntensity: 1, // How much colors shift (0.1 = subtle, 0.5 = rainbow)
          phaseOffset: 5, // Phase difference between slices (0.5 = moderate, 1.5 = chaotic)
        },
      },
    },
  },
  threeD: {
    enabled: true,
    depth: {
      desktop: 5,
      mobile: 5,
    },
    squash: 1,
    light: {
      azimuthDeg: -45,
      elevationDeg: 62,
    },
    sideOpacity: {
      top: 0.55,
      bottom: 0.18,
    },
    rimHighlight: {
      width: 1.4,
      opacity: 0.38,
    },
    topHighlight: {
      intensity: 0.45,
      radiusFraction: 0.82,
    },
    reflection: {
      speed: 0.1,
      width: 0.22,
      intensity: 0.52,
    },
    shadow: {
      scaleX: 1.12,
      scaleY: 0.46,
      offsetYPx: 16,
      blur: 34,
      opacity: 0.28,
    },
    parallax: {
      maxOffsetPx: 8,
      damping: 0.18,
    },
    electric: {
      intensity: 0.5,
      width: 0.15,
      colors: {
        primary: "rgba(250, 250, 250, 0.6)",
        secondary: "rgba(250, 250, 250, 0.4)",
        tertiary: "rgba(250, 250, 250, 0.2)",
        quaternary: "rgba(250, 250, 250, 0.1)",
      },
      arcCount: 3,
      arcThickness: 2.5,
      particlesEnabled: false,
      particleColors: null,
      streakSpeedMultiplier: 2.5,
      particleSpeedMultiplier: 0.5,
    },
    ambientGlow: {
      innerOpacity: 0.15,
      outerOpacity: 0.05,
      pulseSpeed: 0.6,
      innerColor: "rgba(118, 183, 229, 1)",
      outerColor: "rgba(7, 18, 57, 1)",
    },
    seamOffsetRad: 0,
  },
};

export const TABLE_GLASS_EFFECT = {
  enabled: true,
  excludeHeader: true,
  rowHoverEffect: {
    enabled: true,
    // Subtle spotlight effect
    color: "rgba(255, 255, 255, 0.03)", // Very faint white/blue tint
    borderColor: "rgba(255, 255, 255, 0.15)", // Subtle border reveal
    spotlightRadius: 500, // Large soft radius
  },
  chromaticAberration: {
    enabled: true, // Disabled for cleaner look
    offset: 2,
    opacity: 0.5,
  },
  // Override specific 3D settings for the table to be more subtle than the chart
  threeD: {
    ...PIE_CHART_GLASS_EFFECT.threeD,
    electric: {
      ...PIE_CHART_GLASS_EFFECT.threeD.electric,
      enabled: false, // Configurable toggle
      intensity: 0.1, // Reduced intensity
      width: 0.1, // Thinner trails
      arcThickness: 1, // Thinner lines
      streakSpeedMultiplier: 1, // Slower, more elegant movement
      colors: {
        primary: "rgba(255, 255, 255, 0.4)",
        secondary: "rgba(255, 255, 255, 0.2)",
        tertiary: "rgba(255, 255, 255, 0.05)",
        quaternary: "rgba(255, 255, 255, 0.0)",
      },
    },
    reflection: {
      enabled: true,
      speed: 0.05,
      intensity: 0.1, // Subtle
      width: 0.5, // Wider, softer band
      color: "rgba(255, 255, 255, 1)",
      fadeZone: 0.15, // Smooth fade at wrap point (0-1, higher = longer fade)
    },
  },
};

export const MARQUEE_CONFIG = {
  enabled: false,
  // Size multiplier for marquee content (1 = normal, 2 = twice as large)
  sizeMultiplier: 2,
  animationDuration: 20, // seconds for one full loop
  // Direction: 1 = right-to-left (default), -1 = left-to-right
  direction: -1,
};

export const TILT_EFFECT = {
  enabled: false,
};

export const PERLIN_BACKGROUND_SETTINGS = {
  enabled: false,
  blendMode: "screen",
  opacity: 0.85,
  tint: [1, 1, 1],
  sizeFactor: 0.5,
  speed: 0.001,
  angle: 0,
  respectReducedMotion: true,
  maxPixelRatio: 10,
};

export const GRAPH_BACKGROUND_IMAGE = {
  enabled: true,
};
